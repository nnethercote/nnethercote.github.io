---
layout: post
title: How to speed up the Rust compiler in 2022
---

Between 2016 and 2020 I wrote a series of blog posts called ["How to speed up
the Rust
compiler"](https://blog.mozilla.org/nnethercote/2020/09/08/how-to-speed-up-the-rust-compiler-one-last-time/).
These were mostly about my work on the Rust compiler, plus some updates on the
progress on the Rust compiler's speed in general.

I am now back on the Rust bandwagon as a member of Futurewei's Rust team, and
it's time to start up the blog series again.

## Successes

In the past few months I have landed some PRs that improved things.

[#90746](https://github.com/rust-lang/rust/pull/90746): This PR changed a hot
but non-critical `assert!` to a `debug_assert!`, meaning it isn't run in
release builds, for wins of up to 5% on two benchmarks.

[#91246](https://github.com/rust-lang/rust/pull/91246): `Layout::array` is a
function, involved with vector growth, that is instantiated frequently. This PR
made it more concise, reducing the amount of generated LLVM IR, and reducing
compile times by up to 4% on a few benchmarks, with sub-1% improvements on lots
of benchmarks, though the results were a bit noisy.

[#91844](https://github.com/rust-lang/rust/pull/91844/): This PR eliminated the
`ObligationCauseData` structure, reducing allocation rates, for some sub-1%
wins in lots of benchmarks.

[hashbrown #305](https://github.com/rust-lang/hashbrown/pull/305): rustc uses
hash tables heaviy, and I discovered that approximately one third of all
non-modifying hash table lookups are on an empty table! `hashbrown` would
nonetheless hash the inputs and perform a normal lookup in the case. This PR
changed it to fail immediately if the table is empty, for one win of 11% and
lots in the 1-4% range. This change was later merged into rustc as part of the
`hashbrown` update in
[#92998](https://github.com/rust-lang/rust/pull/92998).

[#91948](https://github.com/rust-lang/rust/pull/91948): This PR, co-authored
with [camelid](https://github.com/camelid), avoided lots of allocations in
rustdoc caused by symbol-to-string conversions, for good wins across all
rustdoc benchmarks of up to 5%.

[#92604](https://github.com/rust-lang/rust/pull/92604): This PR optimized
LEB128 reading during metadata encoding (yet
[again](https://github.com/rust-lang/rust/pull/69050)) for wins of up to 3%
across many benchmarks.

[#93066](https://github.com/rust-lang/rust/pull/93066): The `Decoder` trait
used for metadata decoding was fallible, using `Result` throughout. But
decoding failures should only happen if something highly unexpected happens
(e.g. metadata is corrupted) and on failure the calling code would just abort.
This PR changed `Decoder` to be infallible throughout—panicking immediately
instead of panicking slightly later—thus avoiding lots of pointless `Result`
propagation, for wins across many benchmarks of up to 2%.

[#93148](https://github.com/rust-lang/rust/pull/93148): rustc uses
[interning](https://en.wikipedia.org/wiki/String_interning) pervasively, for
strings and many other internal types. Interned types are guaranteed unique and
can be compared and hashed cheaply (by considering just the pointer, rather
than the contents), but some of the interned types weren't taking advantage of
that. This large PR overhauled the types used for interning so they were more
consistent, for wins across many benchmarks of up to 4%.

## Failures

But not everything I tried worked.

- I tried to speed up lexing for the [`externs` stress
  test](https://github.com/rust-lang/rustc-perf/blob/master/collector/benchmarks/externs/src/lib.rs)
  by changing the handling of the first char in new tokens, but it didn't help.
- I tried shrinking various arena-allocated types, such as `Ty` and
  `Predicate`, but it didn't help enough to be worth the effort.
- I drafted a dead store elimination optimization pass for MIR, inspired by the
  presence of obviously redundant code relating to drop flags. It worked, but
  the measurable performance benefits were negligible, and not worth the extra
  code.
- I tried various ways to improve the representation of vectors use with
  `ast::PathSeg` and `AttrVec`, without success.
- I tried to [further](https://github.com/rust-lang/rust/pull/72013) optimize
  code relating to vector growth to minimize LLVM IR generation, but
  [failed](https://github.com/rust-lang/rust/pull/91848) to do it in a way that
  didn't reduce the speed of the compiled code.
- I tried changing the minimum capacity of non-empty Hash tables from 3 to 7.
  This gave some small (1-2%) performance wins, but increased peak memory usage
  by more (5-10%) and so wasn't worth it.
- I tried [numerous
  things](https://nnethercote.github.io/2021/12/08/a-brutally-effective-hash-function-in-rust.html)
  to improve the `FxHasher` algorithm used by rustc's hash tables, without
  success.
- I tried increasing the buffer size used by `StableHasher`, which is used
  with incremental compilation, but caused a slight performance regression. 
- I tried some tweaks with interning: pre-interning some common interned
  values, caching some recently interned values, and avoiding a double lookup
  when interning symbols. None of them helped.
- I tried speeding up `find_library_crate` and failed, though some 
  clean-ups I did along the way [were
  merged](https://github.com/rust-lang/rust/pull/93608).
- I tried tweaking how `TypeFoldable`/`TypeFolder`/`TypeVisitor` work, without
  success, though it did lead to some [better
  documentation](https://github.com/rust-lang/rust/pull/93758).
- I tried a bunch of things to get jemalloc to provide accurate actual sizes of
  allocated blocks, without success. (The design of various Rust and jemalloc
  API boundaries made this task more difficult than I would have liked.) I also
  experimented with jemalloc's "sized deallocation" feature, which several
  people assured me would be a win, but it slowed things down. The way jemalloc
  is hooked into rustc is quite messy and at least I was able to [clarify it a
  little](https://github.com/rust-lang/rust/pull/92222).

You can see that I had more failures than successes. Finding performance wins
is a lot harder than it used to be. Much of the low-hanging fruit has been
plucked, and my success rate is down. Running the usual profilers on the [usual
benchmarks](https://github.com/rust-lang/rustc-perf/tree/master/collector/benchmarks)
(and only measuring the final crate of each benchmark, not the whole
compilation graph) is less effective than before.

So what now?

## Next steps

Fortunately, there is a path forward. [lqd](https://github.com/lqd/) recently
started working full-time on compiler performance, and he did a [large data
gathering exercise](https://github.com/lqd/rustc-benchmarking-data), running a
variety of profilers across almost 800 of the most popular crates on
[crates.io](https://crates.io/). This included both intra-crate and
cross-project measurements. The results give us insight into compiler
performance across a much larger range of real-world code than the benchmark
suite, which has 46 benchmarks, only half of which are derived from real-world
crates.

I have written [an analysis](https://hackmd.io/mxdn4U58Su-UQXwzOHpHag?view) of
the gathered data, pulling out interesting findings. Things like:
- Some parts of the compiler are hot for some crates, but these don't show up
  in the existing benchmarks. Macro parsing is the most extreme example, and
  looks likely to be quite optimizable.
- Certain crates are both widely used and slow to compile, such as
  `syn`/`quote`/`proc-macro2`. Can they be improved?
- Even trivial build scripts seem surprisingly slow to compile. Why is that?
- Our benchmark suite has versions of numerous popular crates that are 3 or 4
  years old. We should update them, and possibly add/remove some.
- Cargo's scheduling may have room for improvement.

This analysis has informed a
[roadmap](https://hackmd.io/YJQSj_nLSZWl2sbI84R1qA?view) for compiler
performance work in 2022. I finished the draft analysis and roadmap documents
just yesterday, but they are already bearing fruit...

[#93984](https://github.com/rust-lang/rust/pull/93984/): This PR introduced an
optimized representation for large bitsets, which greatly reduces the peak
memory requirements for a few crates (by up to 60%!), and also avoids a lot of
memory copying, for speed wins of up to 14%. Pleasingly, this fixed the 
[final outstanding performance
regression](https://github.com/rust-lang/rust/issues/54208) from the
introduction of the "new" borrow checker back in 2018!

[#94316](https://github.com/rust-lang/rust/pull/94316): This PR optimized the
processing of string literals containing escapes, for up to 7% wins on a few
popular crates.

I am hopeful that this new roadmap will lead to more sizeable improvements like
these.

## General progress

From the period [2021-11-11 to
2022-02-25](https://perf.rust-lang.org/compare.html?start=2021-11-11&end=2022-02-25&stat=wall-time)
there were 303 improvements to the results of the rustc benchmark suite, many
of which were over 10%, and only 21 regressions, as the following screenshot
summarizes.

![rustc-perf wall-time 2021-11-11 to 2022-02-25](/images/2022/02/25/rustc-perf-wall-time-2021-11-11-to-2022-02-25.png)

For rustc developers there was the additional nice result that rustc bootstrap
times dropped by 10%.

This is a healthy result for this 3.5 month period. It is due to the efforts of
many people, and continues the long trend of performance improvements.
