---
layout: post
title: How to speed up the Rust compiler in March 2024
---

It has been over six months since my [last
update](https://nnethercote.github.io/2023/08/25/how-to-speed-up-the-rust-compiler-in-august-2023.html)
on the Rust compiler's performance. Time for an update.

## Big wins

Let's start with some big improvements. This list isn't comprehensive, it's
just some things I noticed over this time period. The information about metrics
at the top of [this
post](https://nnethercote.github.io/2022/10/27/how-to-speed-up-the-rust-compiler-in-october-2022.html)
still applies.

[#115554](https://github.com/rust-lang/rust/pull/115554): There are many build
configuration choices that can affect the performance of built Rust binaries.
One choice is to build with [a single codegen
unit](https://nnethercote.github.io/perf-book/build-configuration.html#codegen-units),
which increases build times but can improve runtime speed and binary size. In
this PR [Jakub Beránek](https://github.com/Kobzol) made the Rust compiler
itself be built with a single codegen unit on Linux. This gave a [mean
wall-time reduction of 1.57% across all benchmark
results](https://perf.rust-lang.org/compare.html?start=c16823d757b376f90c5f5cbd542ce83235befbc4&end=871407a0341262d2a86703ca43b449d35fa5f236&stat=wall-time&nonRelevant=true),
a [mean max-rss reduction of 1.96% across all
results](https://perf.rust-lang.org/compare.html?start=c16823d757b376f90c5f5cbd542ce83235befbc4&end=871407a0341262d2a86703ca43b449d35fa5f236&stat=max-rss&nonRelevant=true),
and also reduced the size of the `rustc` binary. This change has not yet been
done for Windows or Mac builds because the improvements were smaller, but it
may happen soon.

[#117727](https://github.com/rust-lang/rust/pull/117727): In this PR, [Ben
Kimock](https://github.com/saethlin/) made all `Debug::fmt` methods generated
via `#[derive(Debug)]` be marked with `#[inline]`. This was a small,
innocuous-sounding change that gave amazing results: a [mean wall-time
reduction of 1.33% across all benchmark
results](https://perf.rust-lang.org/compare.html?start=eae4135939881ae730342bd336ae6302c3787e27&end=0f44eb32f1123ac93ab404d74c295263ce468343&stat=wall-time&nonRelevant=true).
and a [mean binary size reduction of 1.32% across all release build
results](https://perf.rust-lang.org/compare.html?start=eae4135939881ae730342bd336ae6302c3787e27&end=0f44eb32f1123ac93ab404d74c295263ce468343&stat=size%3Alinked_artifact&nonRelevant=true&doc=false&debug=false&check=false&incrFull=false&incrUnchanged=false&incrPatched=false).

[#119977](https://github.com/rust-lang/rust/pull/119977): In this PR, [Mark
Rousskov](https://github.com/Mark-Simulacrum) introduced a cache that helped
avoid many hash table lookups within the compiler. This gave a [mean wall-time
reduction of 1.20% across all benchmark
results](https://perf.rust-lang.org/compare.html?start=92f2e0aa62113a5f31076a9414daca55722556cf&end=098d4fd74c078b12bfc2e9438a2a04bc18b393bc&stat=wall-time&nonRelevant=true).
The idea for this first arose [6.5 years
ago](https://github.com/rust-lang/rust/issues/45275)!

[#120055](https://github.com/rust-lang/rust/pull/120055): In this PR, [Nikita
Popov](https://github.com/nikic) upgraded the LLVM version used by the compiler
to LLVM 18. This gave a [mean wall-time reduction of 0.87% across all benchmark
results](https://perf.rust-lang.org/compare.html?start=bc1b9e0e9a813d27a09708b293dc2d41c472f0d0&end=eaff1af8fdd18ee3eb05167b2836042b7d4315f6&stat=wall-time&nonRelevant=true).
This is the latest in a long run of LLVM updates that have made rustc faster.
Fantastic work from the LLVM folks!

In other big news, the Cranelift codegen backend is now available for [general
use](https://nnethercote.github.io/perf-book/build-configuration.html#cranelift-codegen-back-end)
on x86-64/Linux and ARM/Linux. It is an alternative to the standard LLVM
codegen backend used by rustc, and is designed to reduce compile times at the
cost of lower generated code quality. Give it a try for your debug builds! This
is the culmination of [a lot of
work](https://bjorn3.github.io/2023/10/31/progress-report-oct-2023.html) by
[bjorn3](https://github.com/bjorn3).

Finally, Jakub greatly reduced the size of compiled binaries by [excluding
debug info by
default](https://kobzol.github.io/rust/cargo/2024/01/23/making-rust-binaries-smaller-by-default.html).
For small programs this can reduce their size on disk by up to 10x!

## My (lack of) improvements

For the first time ever, I'm writing one of these posts without having made any
improvements to compile speed myself. I have always used a profile-driven
optimization strategy, and the profiles you get when you measure rustc these
days are incredibly flat. It's hard to find improvements when the hottest
functions only account for 1% or 2% of execution time. Because of this I have
been working on things unrelated to compile speed.

That doesn't mean there are no speed improvements left to be made, as the
previous section shows. But they are much harder to find, and often require
domain-specific insights that are hard to get when fishing around with a
general-purpose profiler. And there is always other useful work to be done.

## General Progress

For the period 2023-08-23 to 2024-03-04 we had some excellent overall
performance results.

First,
[wall-time](https://perf.rust-lang.org/compare.html?start=97fff1f2ed01f6f7c0c204530b693c74d88c2105&end=50e77f133f8eb1f745e05681163a0143d6c4dd7d&stat=wall-time&nonRelevant=true):

- There were 526 results measured across 43 benchmarks.
- 437 of these were improvements, and 89 were regressions. The mean change was
  a reduction of 7.13%, and plenty of the reductions were in the double digits.
  (In my [last
  post](https://nnethercote.github.io/2023/08/25/how-to-speed-up-the-rust-compiler-in-august-2023.html)
  the equivalent reduction was also 7.13%. Quite the coincidence!)

Next, [peak memory usage](https://perf.rust-lang.org/compare.html?start=97fff1f2ed01f6f7c0c204530b693c74d88c2105&end=50e77f133f8eb1f745e05681163a0143d6c4dd7d&stat=max-rss&nonRelevant=true):
- Again, there were 526 results measured across 43 benchmarks.
- 367 of these were improvements, and 159 were regressions. The mean change was
  a 2.05% reduction, and most of the changes were in the single digits.

Finally, [binary
size](https://perf.rust-lang.org/compare.html?start=97fff1f2ed01f6f7c0c204530b693c74d88c2105&end=50e77f133f8eb1f745e05681163a0143d6c4dd7d&stat=size%3Alinked_artifact&nonRelevant=true):
- There were 324 results measured across 43 benchmarks.
- 318 of these were improvements, and 6 were regressions. The mean change was
  a 28.03% reduction, and almost every result was a double-digit reduction.
- If we restrict things to [non-incremental release
  builds](https://perf.rust-lang.org/compare.html?start=97fff1f2ed01f6f7c0c204530b693c74d88c2105&end=50e77f133f8eb1f745e05681163a0143d6c4dd7d&stat=size%3Alinked_artifact&nonRelevant=true&incrFull=false&incrUnchanged=false&incrPatched=false&check=false&debug=false&doc=false),
  which is the most interesting case for binary size, there were 42
  improvements, 1 regression, and the mean change was a reduction of 37.08%.
  The `helloworld` benchmark saw a whopping 91.05% reduction.
- These improvements are mostly to the omission of debug info mentioned above,
  plus some metadata improvements made by Mark.

For all three metrics, all but a handful of results met the significance
threshold. I haven't bothered separating those results because they made little
difference to the headline numbers. As always, these measurements are done on
Linux.

Finally, Jakub recently
[observed](https://twitter.com/Beranek1582/status/1760546947352453317) that
compile times (as measured on Linux by the benchmark suite) dropped by 15%
between February 2023 and February 2024. The corresponding reductions over each
of the preceding three years were 7%, 17%, and 13%, and the reduction over the
whole four year period was 37%. There is something to be said for steady,
continuous improvements over long periods of time.
