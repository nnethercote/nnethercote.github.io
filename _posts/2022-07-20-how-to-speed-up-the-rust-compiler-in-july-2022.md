---
layout: post
title: How to speed up the Rust compiler in July 2022
---

Let's look at some of the progress on Rust compiler speed made since my 
[last post](https://nnethercote.github.io/2022/04/12/how-to-speed-up-the-rust-compiler-in-april-2022.html). I will start with some important changes made by other people.

### Windows PGO

[Profile-guided
optimization](https://en.wikipedia.org/wiki/Profile-guided_optimization) is a
technique for producing faster programs. It has three steps.
- Compile a program in a special way that adds instrumentation.
- Run the compiled program on a representative workload. The instrumentation
  will record data about the program's execution.
- Recompile the program. The compiler can use the gathered data to better
  optimize the final code.

PGO can be highly effective, and we have been using it for some time when
building the Rust compiler on Linux.

[#96978](https://github.com/rust-lang/rust/pull/96978): In this PR,
[@lqd](https://github.com/lqd) enabled PGO for the Rust compiler on Windows,
with help from [@Kobzol](https://github.com/Kobzol) and others. PGO is fragile
and tricky to get working on large programs, and it took much trial and error
to it configured correctly. But the effort was worth it, with 10-20% wins
across most invocations in the benchmark suite, with an average of 12.5%!
Amazing.

We'd love to get PGO working on Mac as well. Unfortunately, this is challenging
from a CI configuration and maintenance point of view. See the [discussion on
Reddit](https://www.reddit.com/r/rust/comments/vx4wwe/rust_compiler_got_15_faster_on_windows_thanks_to/ifuj866/)
for more details.

For better news on Mac, it seems that the next version of Xcode (14.0) may
include a [much faster
linker](https://developer.apple.com/videos/play/wwdc2022/110362/). We have [one
data
point](https://rust-lang.zulipchat.com/#narrow/stream/131828-t-compiler/topic/ld64.20on.20macOS.20Ventura/near/289539049)
showing it is roughly twice as fast as the current linker for Rust code.

### MIR inlining

[#91473](https://github.com/rust-lang/rust/pull/91743): In this PR
[cjgillot](https://github.com/cjgillot) enabled the MIR inliner. This lets
rustc's frontend do inlining, so it no longer has to rely only on the LLVM
backend to perform inlining. (LLVM still does some inlining, though.) This
change affected compile times for many crates, mostly for the better, with
improvements of up to 10% for primary benchmarks. It cut rustc bootstrap time
by 8.8%. It also [helps the speed of code produced by the Cranelift
backend](https://github.com/rust-lang/rust/pull/91743#issuecomment-1187275690):

> This has improved runtime performance of cg_clif compiled programs by a lot
> (when compiled in release mode). For example rustc compiled using cg_clif now
> builds the standard library in 8 min instead of 22 min.

This change was a lot of work. Great job, @cjgillot!

### Procedural macros

In my last post I said I was planning to look into the performance of
procedural macros. I did make [one
PR](https://github.com/rust-lang/rust/pull/97004) that did a few small
cleanups. But that part of the compiler is tricky and has lower than average
reviewer coverage, which makes progress slow.

In better news, some progress was finally made on a
year-old [proc macro performance PR](https://github.com/rust-lang/rust/pull/86822)
from Nika Layzell, which was producing wins of up to 5% on primary benchmarks
and up to 36% on one procedural macro stress test. The PR was split up and
parts of it landed in
[#98186](https://github.com/rust-lang/rust/pull/98186),
[#98187](https://github.com/rust-lang/rust/pull/98187), and
[#98188](https://github.com/rust-lang/rust/pull/98188).
That leaves only 
[#98189](https://github.com/rust-lang/rust/pull/98189) outstanding at the time
of writing.

### Deriving builtin traits

In June I watched some talks at PLDI and co-located workshops, including a nice
one at LCTES about a paper called [Tighten Rust’s Belt: Shrinking Embedded Rust
Binaries](https://dl.acm.org/doi/abs/10.1145/3519941.3535075). It investigates
why Rust binaries tend to be larger (often by 50% to 100%) than similar C
binaries. There are several reasons, but one of them was the size of the
derived code for types annotated with `#[derive(Debug)]`.

This prompted me to look at the derived code for all the builtin traits:
`Clone`, `Copy`, `Debug`, `Default`, `Hash`, `PartialEq`, `Eq`, `PartialOrd`,
and `Ord`. (I ignored `RustcEncodable` and `RustcDecodable` which were
deprecated in Rust 1.52.) I did this by using `cargo expand` and `rustc
+nightly -Zunpretty=expanded`. Although the LCTES paper focused on binary size,
I figured that improvements could help code size, too.

#### PRs

Over a few weeks I filed a number of PRs that (a) improved the derived code,
and (b) significantly refactored the `rustc_builtin_macros` crate, which is the
part of the compiler that produces the derived code.

- [#98190](https://github.com/rust-lang/rust/pull/98190) (3 commits): Reduces
  number of function calls in derived code for `Debug`.
- [#98376](https://github.com/rust-lang/rust/pull/98376) (5 commits):
  Refactorings and tiny derived code improvements, plus the addition of a test
  that checks derived code—we didn't have one before—that was very useful for
  all the subsequent work.
- [#98741](https://github.com/rust-lang/rust/pull/98741) (12 commits):
  Refactorings.
- [#98446](https://github.com/rust-lang/rust/pull/98446) (3 commits): Replaces
  match destructuring with field accesses in derived code, plus test
  improvements.
- [#98758](https://github.com/rust-lang/rust/pull/98758) (7 commits): Several
  small derive code improvements, plus test improvements.
- [#98915](https://github.com/rust-lang/rust/pull/98915) (8 commits):
  Refactorings.
- [#99046](https://github.com/rust-lang/rust/pull/99046) (11 commits): More
  small derive code improvements, plus test improvements.

On many real-world crates these improvements [reduced compile times by
1-7%](https://github.com/rust-lang/rust/pull/99446). On the `derive` stress
test they win up to 25%. The average across every result in the benchmark suite
was a 1% win. I have also seen some small binary size reductions, though I
haven't measured these carefully.

I also have a [PR open](https://github.com/rust-lang/rust/pull/98655) to stop
deriving `ne` methods, because the default `ne` method is always good enough.
It's currently stalled because of a suggestion that this requires adding a new
lint for deprecating the overriding of particular methods.

Finally, I also have a [PR open](https://github.com/serde-rs/serde/pull/2250)
on Serde, to reduce the size of the derived code for the `Serialize` and
`Deserialize` traits, which reduces compile times on some stress tests by up to
30%. Interestingly, the derived code for these traits is *much* larger than the
derived code for the builtin traits, especially for `Deserialize`.

#### Details of improvements

Here are some example diffs showing the improvement between the old and new
derived code for the builtin traits.

This one shows how the `fmt` method for a struct with two fields went from
containing four function calls to one function call. It also shows how match
destructuring was replaced with field accesses.

```
 struct Point { x: u32, y: u32 }

 impl ::core::fmt::Debug for Point {
     fn fmt(&self, f: &mut ::core::fmt::Formatter) -> ::core::fmt::Result {
-        match *self {
-            Self {
-                x: ref __self_0_0,
-                y: ref __self_0_1,
-            } => {
-                let debug_trait_builder = &mut ::core::fmt::Formatter::debug_struct(f, "Point");
-                let _ = ::core::fmt::DebugStruct::field(debug_trait_builder, "x", &&(*__self_0_0));
-                let _ = ::core::fmt::DebugStruct::field(debug_trait_builder, "y", &&(*__self_0_1));
-                ::core::fmt::DebugStruct::finish(debug_trait_builder)
-            }
-        }
+        ::core::fmt::Formatter::debug_struct_field2_finish(f, "Point", "x", &&self.x, "y", &&self.y)
     }
 }
```

The next one shows a similar improvement, but for a struct with more than five
fields, which uses a slightly different approach.
```
 struct Big { b1: u32, b2: u32, b3: u32, b4: u32, b5: u32, b6: u32, b7: u32, b8: u32 }

 impl ::core::fmt::Debug for Big {
     fn fmt(&self, f: &mut ::core::fmt::Formatter) -> ::core::fmt::Result {
-        match *self {
-            Self {
-                b1: ref __self_0_0,
-                b2: ref __self_0_1,
-                b3: ref __self_0_2,
-                b4: ref __self_0_3,
-                b5: ref __self_0_4,
-                b6: ref __self_0_5,
-                b7: ref __self_0_6,
-                b8: ref __self_0_7,
-            } => {
-                let debug_trait_builder = &mut ::core::fmt::Formatter::debug_struct(f, "Big");
-                let _ = ::core::fmt::DebugStruct::field(debug_trait_builder, "b1", &&(*__self_0_0));
-                let _ = ::core::fmt::DebugStruct::field(debug_trait_builder, "b2", &&(*__self_0_1));
-                let _ = ::core::fmt::DebugStruct::field(debug_trait_builder, "b3", &&(*__self_0_2));
-                let _ = ::core::fmt::DebugStruct::field(debug_trait_builder, "b4", &&(*__self_0_3));
-                let _ = ::core::fmt::DebugStruct::field(debug_trait_builder, "b5", &&(*__self_0_4));
-                let _ = ::core::fmt::DebugStruct::field(debug_trait_builder, "b6", &&(*__self_0_5));
-                let _ = ::core::fmt::DebugStruct::field(debug_trait_builder, "b7", &&(*__self_0_6));
-                let _ = ::core::fmt::DebugStruct::field(debug_trait_builder, "b8", &&(*__self_0_7));
-                ::core::fmt::DebugStruct::finish(debug_trait_builder)
-            }
-        }
+        let names: &'static _ =
+            &["b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8"];
+        let values: &[&dyn ::core::fmt::Debug] = &[
+            &&self.b1, &&self.b2, &&self.b3, &&self.b4, &&self.b5, &&self.b6,
+            &&self.b7, &&self.b8,
+        ];
+        ::core::fmt::Formatter::debug_struct_fields_finish(
+            f, "Big", names, values,
+        )
     }
 }
```
The next one shows how redundant assertions (seen in the derived functions for
`Clone` and `Eq`) are avoided when there are multiple fields with the same
type. It also shows removal of an unnecessary block.
```
 impl ::core::cmp::Eq for Big {
     fn assert_receiver_is_total_eq(&self) -> () {
-        {
-            let _: ::core::cmp::AssertParamIsEq<u32>;
-            let _: ::core::cmp::AssertParamIsEq<u32>;
-            let _: ::core::cmp::AssertParamIsEq<u32>;
-            let _: ::core::cmp::AssertParamIsEq<u32>;
-            let _: ::core::cmp::AssertParamIsEq<u32>;
-            let _: ::core::cmp::AssertParamIsEq<u32>;
-            let _: ::core::cmp::AssertParamIsEq<u32>;
-            let _: ::core::cmp::AssertParamIsEq<u32>;
-        }
+        let _: ::core::cmp::AssertParamIsEq<u32>;
     }
 }
```
The next one shows removal of uninteresting boilerplate code for the degenerate
case of an empty struct. There are similar improvements for other degenerate
cases, such as empty enums and enums with a single variant. These aren't common
but when I was neck-deep in `rustc_builtin_macros` it was fairly
straightforward (and very satisfying) to make them work nicely.
```
 struct Empty;

 impl ::core::cmp::PartialEq for Empty {
     #[inline]
     fn eq(&self, other: &Empty) -> bool {
-        match *other {
-            Self => match *self {
-                Self => true,
-            },
-        }
+        true
     }
 }
```
The next one shows how field accesses can work even on a packed struct, as long
as it impls `Copy`, by using an extra block which forces a copy. This is a
trick I learned from [@scottmcm](https://github.com/scottmcm).
```
 #[repr(packed)]
 struct PackedCopy(u32);

 impl ::core::hash::Hash for PackedCopy {
     fn hash<__H: ::core::hash::Hasher>(&self, state: &mut __H) -> () {
-        match *self {
-            Self(__self_0_0) => ::core::hash::Hash::hash(&(__self_0_0), state),
-        }
+        ::core::hash::Hash::hash(&{ self.0 }, state)
     }
 }
```
The next one shows various improvements for enums: the removal of unnecessary
1-tuple patterns, `ref` keywords, parentheses, and sigils.
```
 impl ::core::clone::Clone for Fielded {
     #[inline]
     fn clone(&self) -> Fielded {
-        match (&*self,) {
-            (&Fielded::X(ref __self_0),) => Fielded::X(::core::clone::Clone::clone(&(*__self_0))),
-            (&Fielded::Y(ref __self_0),) => Fielded::Y(::core::clone::Clone::clone(&(*__self_0))),
-            (&Fielded::Z(ref __self_0),) => Fielded::Z(::core::clone::Clone::clone(&(*__self_0))),
-        }
+        match self {
+            Fielded::X(__self_0) => Fielded::X(::core::clone::Clone::clone(__self_0)),
+            Fielded::Y(__self_0) => Fielded::Y(::core::clone::Clone::clone(__self_0)),
+            Fielded::Z(__self_0) => Fielded::Z(::core::clone::Clone::clone(__self_0)),
+        }
     }
 }
```
The next one shows how struct comparisons improved, by removing a useless
`match` on the result of the final field comparison.
```
 impl ::core::cmp::Ord for Point {
     #[inline]
     fn cmp(&self, other: &Point) -> ::core::cmp::Ordering {
-        match *other {
-            Self {
-                x: ref __self_1_0,
-                y: ref __self_1_1,
-            } => match *self {
-                Self {
-                    x: ref __self_0_0,
-                    y: ref __self_0_1,
-                } => match ::core::cmp::Ord::cmp(&(*__self_0_0), &(*__self_1_0)) {
-                    ::core::cmp::Ordering::Equal => {
-                        match ::core::cmp::Ord::cmp(&(*__self_0_1), &(*__self_1_1)) {
-                            ::core::cmp::Ordering::Equal => ::core::cmp::Ordering::Equal,
-                            cmp => cmp,
-                        }
-                    }
-                    cmp => cmp,
-                },
-            },
-        }
+        match ::core::cmp::Ord::cmp(&self.x, &other.x) {
+            ::core::cmp::Ordering::Equal => ::core::cmp::Ord::cmp(&self.y, &other.y),
+            cmp => cmp,
+        }
     }
 }
```
The next one shows how hashing of enums improved, by hashing the discriminant
once at the start instead of in every `match` arm.
```
 enum Fielded { X(u32), Y(bool), Z(Option<i32>) }

 impl ::core::hash::Hash for Fielded {
     fn hash<__H: ::core::hash::Hasher>(&self, state: &mut __H) -> () {
-        match (&*self,) {
-            (&Fielded::X(ref __self_0),) => {
-                ::core::hash::Hash::hash(&::core::intrinsics::discriminant_value(self), state);
-                ::core::hash::Hash::hash(&(*__self_0), state)
-            }
-            (&Fielded::Y(ref __self_0),) => {
-                ::core::hash::Hash::hash(&::core::intrinsics::discriminant_value(self), state);
-                ::core::hash::Hash::hash(&(*__self_0), state)
-            }
-            (&Fielded::Z(ref __self_0),) => {
-                ::core::hash::Hash::hash(&::core::intrinsics::discriminant_value(self), state);
-                ::core::hash::Hash::hash(&(*__self_0), state)
-            }
-        }
+        let __self_tag = ::core::intrinsics::discriminant_value(self);
+        ::core::hash::Hash::hash(&__self_tag, state);
+        match self {
+            Fielded::X(__self_0) => ::core::hash::Hash::hash(__self_0, state),
+            Fielded::Y(__self_0) => ::core::hash::Hash::hash(__self_0, state),
+            Fielded::Z(__self_0) => ::core::hash::Hash::hash(__self_0, state),
+        }
     }
 }
```
The next one shows how comparisons on discriminants were streamlined for enums.
```
 enum Fieldless { A, B, C }

 impl ::core::cmp::Ord for Fieldless {
     #[inline]
     fn cmp(&self, other: &Fieldless) -> ::core::cmp::Ordering {
-        {
-            let __self_vi = ::core::intrinsics::discriminant_value(&*self);
-            let __arg_1_vi = ::core::intrinsics::discriminant_value(&*other);
-            if true && __self_vi == __arg_1_vi {
-                match (&*self, &*other) {
-                    _ => ::core::cmp::Ordering::Equal,
-                }
-            } else {
-                ::core::cmp::Ord::cmp(&__self_vi, &__arg_1_vi)
-            }
-        }
+        let __self_tag = ::core::intrinsics::discriminant_value(self);
+        let __arg1_tag = ::core::intrinsics::discriminant_value(other);
+        ::core::cmp::Ord::cmp(&__self_tag, &__arg1_tag)
     }
 }
```

#### Discussion

The derived code for all builtin traits is now close to optimal, and very
similar to what you would write by hand. You can see more examples in the
compiler's test suite: [Rust
code](https://github.com/rust-lang/rust/blob/master/src/test/ui/deriving/deriving-all-codegen.rs),
[expanded
output](https://github.com/rust-lang/rust/blob/master/src/test/ui/deriving/deriving-all-codegen.stdout).

In my [last
post](https://nnethercote.github.io/2022/04/12/how-to-speed-up-the-rust-compiler-in-april-2022.html),
I described some improvements I made to the compiler's handling of declarative
macros. This work on derived code had some similarities: it was spread over a
number of PRs, and involved both a combination of refactorings and
optimizations. But it also had some differences.

My declarative macro work was very exploratory. I didn't have a clear idea
where things would end up, and I had to feel my way through the changes. In
comparison, these deriving improvements were relatively straightforward. As
soon as I looked at the derived code it was clear what improvements were
possible. I had to get familiar with `rustc_builtin_macros` to make these
improvements, but that crate is fairly straightforward for anyone with
compiler experience.

They key part here was the prompt from the LCTES talk to even look at the
derived code in the first place, which was something I'd never thought to do.
When looking at profiles of rustc execution the compilation of derived code
doesn't show up any differently to the compilation of hand-written code, so
it was easy to overlook the difference. It's a nice reminder on the value of
external input and a diversity of viewpoints and experience.

It's also a good reminder that one of the best ways to reduce compile times is
to simply push less code through the compiler. Derived code (either builtin or
from proc macros) can increase program size significantly, in a way that isn't
obvious to most Rust programmers.

### Miscellaneous

Let's now look at some smaller improvements in a few different areas.

#### Const generics

When considering which types implement which traits, the compiler sometimes
does many type comparisons. The full comparisons are moderately expensive, so
the compiler has a "fast reject" operation that in many case can cheaply
determine if two types are unequal, thus avoiding the full comparison.

This fast reject operation did not handle comparisons of the form `Foo<M>` vs
`Foo<N>` where `M` and `N` are different const integers (e.g. `Foo<1>` vs
`Foo<2>`). A small number of crates instantiate such types with hundreds or
thousands of different const values.

[#97136](https://github.com/rust-lang/rust/pull/97136), 
[#97345](https://github.com/rust-lang/rust/pull/97345): In these PRs
[@lcnr](https://github.com/lcnr) and I improved the fast reject operation to
cover more cases, including the `Foo<M>` vs `Foo<N>` case. This gave some [huge
compile time
reductions](https://github.com/rust-lang/rust/pull/97345#issuecomment-1136605020)
on a few crates: up to 69% on `bitmaps-3.1.0`, up to 59% on `nalgebra`, up to
39% on `secrecy-0.8.0`, etc. Wins this large on real-world crates are rare and
nice to see.

#### Parser

[#96210](https://github.com/rust-lang/rust/pull/96210): In this PR I made many
micro-optimizations in and around the `TokenCursor` type used in the parser,
giving wins of up to 17% on the `tt-muncher` stress test and wins of 1-2%
across many real-world benchmarks.

[#96683](https://github.com/rust-lang/rust/pull/96683): In this PR I
micro-optimized one function involved in parsing, giving wins across many
benchmarks, the best being 7%.

#### jemalloc

[#96790](https://github.com/rust-lang/rust/pull/96790): In this PR @lqd updated
the version of jemalloc used by the compiler to the latest (5.3), which reduced
peak memory usage on many benchmarks, by up to 5% on primary benchmarks and up
to 10% on secondary benchmarks. It also gaves lots of 1-2% speed wins.

#### Metadata

[#97575](https://github.com/rust-lang/rust/pull/97575): A big part of a crate's
metadata is the `lines` list, a difference list of byte offsets to the start of
each line in the source code. The compiler would decompress this list into a
more usable form for `std` when compiling any program, even though it was often
never used. In this PR I made the decompressing step lazy, for wins of up to
15% for tiny programs. Although it's a small win in absolute terms, it makes up
for this by shaving a few milliseconds off almost every invocation of the
compiler.

#### Vectors

[smallvec #282](https://github.com/servo/rust-smallvec/pull/282): In this PR I
improved the speed of `SmallVec::insert` in the case where the item is being
inserted at the end of vector, by avoiding a zero-length `memcpy`. This was a
case that was common in rustc on one benchmark. This change was released in
smallvec 1.8.1. In [#98588](https://github.com/rust-lang/rust/pull/98558) I
then updated the version of `smallvec` used in rustc, for 2% wins on the
`tt-muncher` benchmark. (Thanks to Matt Brubeck for making the 1.8.1 release of
`smallvec`.)

[#98755](https://github.com/rust-lang/rust/pull/98755): In this PR I made the
same change to `Vec::insert`, giving some sub-1% wins on a couple of
benchmarks.

[#96002](https://github.com/rust-lang/rust/pull/96002): `vec.clear()` was
calling `vec.truncate(0)`, which isn't inlined and does more work than is
necessary when clearing the entire vector. In this PR I changed `clear()` to be
more efficient. I saw some wins when profiling locally, but not on CI. I
suspect this is because PGO optimizes `truncate(0)` to be as good as the new
`clear()`. But not all platforms are compiled with PGO, so it was worth
merging.

Finally, if you are using the `tinyvec` crate you should strongly consider
enabling the `rustc_1_55` feature because I discovered that it makes that crate
compile up to twice as fast. [This
issue](https://github.com/Lokathor/tinyvec/issues/161) has the details.

#### Optimizations targeting single crates

Our [prior analysis](https://hackmd.io/mxdn4U58Su-UQXwzOHpHag) identified a
long tail of functions in the compiler that are hot on just one or two crates.
Many of these were not worth the time and effort to improve, but there were a
few easy wins.

[#97936](https://github.com/rust-lang/rust/pull/97936):
`unicode-normalization-0.1.19` has a number of large matches continaing many
range patterns like `'\u{037A}'..='\u{037F}'`. In this PR I optimized the
handling of such ranges, for wins on this crates of up to 19%.

[#98569](https://github.com/rust-lang/rust/pull/98569): In this PR I rearranged
the `finalize_resolutions_in` function to avoid unnecessary work in some cases,
for a small speed win when compiling `c2-chacha-0.3.3`.

[#98654](https://github.com/rust-lang/rust/pull/98654): In this PR I found an
operation in the function `search_for_structural_match_violation` that was
unnecessary, for a small speed win when compiling `pest-2.1.3`.

#### Third party crates

I made a couple of small improvements to crates outside of the compiler.

[pin-project-lite #71](https://github.com/taiki-e/pin-project-lite/pull/71):
During my work earlier in the year on declarative macros I noticed that the
`pin-project-lite` crate had a very large macro called `__pin_project_lite`
with many internal rules. This PR split the macro into several smaller macros.
The performance wins were small (2% at best) but it made the code more
readable, and so was worthwhile if only for that.

[unicode-xid #29](https://github.com/unicode-rs/unicode-xid/pull/29): This PR
changes two large constants from `const` to `static`, reducing the size of the
resulting `.rlib` and `.rmeta` files by about 40KB.

### Roadmap progress

Since last time, the main progress on the [Compiler performance roadmap for
2022](https://hackmd.io/YJQSj_nLSZWl2sbI84R1qA?view) is that the "Hot Code"
part of the "Faster single crate optimization" section has been completed.

The remaining unfinished items are among the more difficult and/or less
well-specified, and I don't expect every item on the list to be completed this
year. Also, there is plenty of work that could be done that doesn't git under
the roadmap. As it says in the introduction, the roadmap is "a rough guide,
rather than a strict prescription". We will keep plugging away at it.

### General Progress

For the period
[2022-04-12 to
2022-07-19](https://perf.rust-lang.org/compare.html?start=2022-04-12&end=2022-07-19&stat=wall-time)
the following screenshot summarizes the results.

![rustc-perf wall-time 2022-04-12 to 2022-07-19](/images/2022/07/20/rustc-perf-wall-time-2022-04-12-to-2022-07-19.png)

There 202 improvements to the results of the rustc benchmark suite, with the
average improvement being 10%. There were 257 results that were not
significantly changed, and 23 results that regressed, with the average
regression being 13.7%, although this was skewed by one 120% regression to a
single `doc` run of one secondary benchmark. Overall, the average result was a
5% improvement.

For rust developers there was also a reduction in bootstrap times of 5%, which
is nice.

Please note that these measurements are done on Linux, and do not include the
12.5% average improvement that Windows users will see from PGO!

This is a healthy result for a three month period, and continues a long trend
of improvements in rustc compiler performance. As Rust grows in popularity
these speed wins benefit an increasing number of people. Thanks to everybody
who contributed!
