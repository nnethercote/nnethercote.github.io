---
layout: post
title: How to speed up the Rust compiler in September 2026
---

My [last
post](https://nnethercote.github.io/2026/07/31/how-to-speed-up-the-rust-compiler-in-july-2026.html)
on the Rust compiler's performance was two months ago and a lot has happened
since then.

## Overall progress

The measurements for the period 2026-07-29 to 2026-09-28 can be seen
[here](https://perf.rust-lang.org/compare.html?start=1a833e16546c2eb012758ddd499964fd8afee29e&stat=wall-time&tab=compile&end=c1070d69382b8d2f2eb65119c738a77d9e324c9e&nonRelevant=true).

The mean wall-time reduction was 4.57%, which is a remarkable improvement in
just two months. Of the 629 benchmark measurements, 555 of them improved and
only 74 regressed. A number of benchmarks saw double-digit percentage
reductions. The technical term for this result is "a sea of green".

## rustdoc

In my last post I mentioned how [Noah Lev](https://github.com/camelid) got some
enormous speed wins on rustdoc. He recently wrote [a
post](https://noahlev.org/blog/2026/08/27/making-rustdoc-faster) explaining in
some detail exactly how he did this. It's an interesting and satisfying read.

## Clippy

[#159642](https://github.com/rust-lang/rust/pull/159642): In this PR
[Jakub Beránek](https://github.com/Kobzol) enabled PGO for Clippy, giving
wall-time improvements across most Clippy benchmarks, in the best case by 18%!

## LLVM update

[#158734](https://github.com/rust-lang/rust/pull/158734): In this PR [Nikita
Popov](https://github.com/nikic) upgraded the LLVM version used by the compiler
to LLVM 23. As often happens when we upgrade LLVM, we saw some nice speedups.
The mean wall-time reduction across all benchmarks was 1.2%, which might not
sound like much but is really impressive for a single PR. Great work from the
LLVM folks!

## The new borrow checker

The new borrow checker, [Polonius](https://en.wikipedia.org/wiki/Polonius)
[Alpha](https://en.wikipedia.org/wiki/Alpha) (no relation to
[Napoleon](https://en.wikipedia.org/wiki/Napoleon_(disambiguation))
[Dynamite](https://www.youtube.com/watch?v=gdZLi9oWNZg)), was
[enabled on
Nightly](https://blog.rust-lang.org/2026/08/04/enabling-polonius-alpha-on-nightly/).
It is more precise than the existing borrow checker and accepts some valid
programs that the old borrow checker would reject. It does do more work than the
old borrow checker, enough to make a measurable difference to compile time in a
minority of cases, including the popular `serde` crate. Fortunately, [Jack
Huey](https://github.com/jackh726) has been on the case.

[#161938](https://github.com/rust-lang/rust/pull/161938): In this PR Jack made
some liveness computations lazy, which reduced instruction counts for `serde`
by 3-5%, and for some other benchmarks by less than 1%.

[#163027](https://github.com/rust-lang/rust/pull/163027): In this PR Jack
adjusted a data structure and tweaked some inlining, for mostly sub-1%
instruction count reductions across numerous benchmarks.

There is more work to be done to reduce the remaining Polonius Alpha
regressions, but it's worth noting that the "sea of green" shows these
regressions were swamped by the many other recent improvements.

## The new trait solver

The new trait solver,
[Penelope](https://en.wikipedia.org/wiki/Anne_Hathaway)
[Hammertime](https://www.youtube.com/watch?v=q8WSdypJ4WA),
*[Ed. note: is that right?]* was also [enabled on
Nightly](https://blog.rust-lang.org/2026/08/21/enabling-next-solver-on-nightly/).

As I said, a lot has been happening.

Like the new borrow checker, the new trait solver is slower in a minority of
cases. [Jana Dönszelmann](https://github.com/jdonszelmann) wrote a [detailed
post](https://donsz.nl/blog/new-solver-performance) about the efforts to
improve the performance of this new solver.

Jana's post is detailed enough that I won't say much more about the large
amount of ongoing work on the new solver, but I will mention in passing the PRs
I made:
[#160479](https://github.com/rust-lang/rust/pull/160479),
[#160605](https://github.com/rust-lang/rust/pull/160605),
[#160801](https://github.com/rust-lang/rust/pull/160801),
[#160892](https://github.com/rust-lang/rust/pull/160892),
[#161077](https://github.com/rust-lang/rust/pull/161077),
and [#161211](https://github.com/rust-lang/rust/pull/161211).
Some of these reduced compile times greatly for certain outlier crates: 50%
here, 25% there, 15% there, and [even
more](https://github.com/rust-lang/rust/issues/159933#issuecomment-5333109889)
on one stress test. And I am not the only one who has made progress here... go
read Jana's post.

## xmakro

New contributor [xmakro](https://github.com/xmakro) continued their run of good
improvements.

[#157281](https://github.com/rust-lang/rust/pull/157281): In this PR xmakro
optimized impl handling when building the specialization graph. This gave a
mean cycle count reduction of 1.58% across all benchmarks, which is huge for a
single PR.

[#158059](https://github.com/rust-lang/rust/pull/158059): In this PR xmakro
optimized one aspect of the loading of incremental compilation data, reducing
instruction counts across multiple benchmarks, in the best case by 6%.

[#160473](https://github.com/rust-lang/rust/pull/160473): In this PR xmakro
avoided some allocations in a hot obligations processing path, reducing
instruction counts across numerous benchmarks, in the best case by 2%.

[#160268](https://github.com/rust-lang/rust/pull/160268): In this PR xmakro
avoided a lot of allocations by changing the old/new trait solver selection
code to use static dispatch instead of dynamic dispatch. This gave mostly
sub-1% instruction count reductions across a number of benchmarks. This hot
allocation path had been showing up in profiles for a while and I had earlier
tried exactly the same idea in
[#155714](https://github.com/rust-lang/rust/pull/155714). But I got regressions
on a couple of benchmarks, possibly due to slightly different choices of where
to place some `#[inline]` attributes. It was good to see this obvious
inefficiency fixed.

## Dataflow analysis

[#160193](https://github.com/rust-lang/rust/pull/160193): In this PR I changed
the CFG traversal algorithm used by the dataflow analyses in the compiler.
These analyses iterate to a fixpoint and the traversal algorithm can affect how
quickly the fixpoint is reached. For most code the new algorithm makes no
difference, but the `cranelift-codegen` crate has one enormous function with
over 18,000 basic blocks. The old algorithm required 1.5 million calls to
`apply_effects_in_block` to reach a fixpoint for the `EverInitializedPlaces`
analysis used by the borrow checker; the new algorithm requires 90,000. This
gave an enormous ~30% wall-time reduction for a `check` build of this crate.

[#160033](https://github.com/rust-lang/rust/pull/160033): In this PR I made
`EverInitializedPlaces` more efficient again, this time by not tracking
unnecessary data for projections. This reduced instruction counts on the
`match-stress` benchmark by 17%, and on a few other benchmarks by less than 1%.

## LLMs

They've gotten very good at certain kinds of analysis. I'm still writing all my
own code and text, because (a) that's paramount, and (b) the [project
policy](https://forge.rust-lang.org/policies/llm-usage.html) requires it, but I
had useful LLM analysis assistance on several of the PRs mentioned in this post.

Anyway, enough about that.

## Miscellaneous

[#160535](https://github.com/rust-lang/rust/pull/160535): In this PR [Chris
Denton](https://github.com/ChrisDenton) increased the default stack size used
by the compiler, which allowed the removal of `ensure_sufficient_stack`, a
manual stack extension mechanism sprinkled about in places prone to high levels
of recursion. There was a lot of discussion about this one because it can be
difficult to decide how to best deal with stack exhaustion. But the performance
effects are clear, with reduced instruction counts across many benchmarks, in
the best case by almost 3%.

[#160506](https://github.com/rust-lang/rust/pull/160506): The project uses a
lot of "rollup" PRs, where multiple PRs are merged together. This is because we
don't have sufficient CI capacity to merge every PR individually. Normally PRs
that affect performance are merged by themselves so we can measure their
effects clearly. For the first time ever, at one point we had so many
performance improvement PRs waiting in the merge queue that [Jonathan
Brouwer](https://github.com/JonathanBrouwer) created a rollup containing 10
performance-improving PRs to keep things moving! This is a good problem to
have. And later on we had
[#162859](https://github.com/rust-lang/rust/pull/162859) which contained four
performance-improving PRs. (You needn't worry about unexpected effects slipping
in because we have the ability to run the perf benchmark suite on the
individual PRs after merging, to make sure each PR had the expected performance
effect.)

[#162747](https://github.com/rust-lang/rust/pull/162747): In this PR I made
some minor improvements to the code that lowers AST to HIR. It was a cleanup
that wasn't expected to affect performance but it reduced instruction counts
across numerous benchmarks, in the best case by 1.5%. Sometimes you get lucky.

## Job status

Tomorrow I will start working at [Hexcat](https://hexcat.nl/) on the [compiler
performance
optimizations](https://goals.rust-lang.org/2026/compiler-performance-optimization.html)
project goal. It's exciting! Many thanks to Mara Bos, Predrag Gruevski, and all
the other people who helped make this happen.

### *Editor's postscript*

<span style="font-size: 14px;">
The new solver's name is not
[Penelope](https://en.wikipedia.org/wiki/Penelope,_Texas)
[Hammer](https://www.youtube.com/watch?v=OJWJE0x7T4Q)[time](https://www.youtube.com/watch?v=Qr0-7Ds79zo); that was a joke.
</span>

#### Author's postscript

<span style="font-size: 12px;">
Its real name is
[Pineapple](https://en.wikipedia.org/wiki/Australian_fifty-dollar_note)
[Häagen-Dazs](https://en.wikipedia.org/wiki/Ben_&_Jerry's).
</span>
