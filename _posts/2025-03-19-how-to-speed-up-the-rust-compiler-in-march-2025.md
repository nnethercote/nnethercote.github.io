---
layout: post
title: How to speed up the Rust compiler in March 2025
---

It has been just over a year since my [last
update](https://nnethercote.github.io/2024/03/06/how-to-speed-up-the-rust-compiler-in-march-2024.html)
on the Rust compiler's performance. Let's get into it. The information about
metrics at the top of [this
post](https://nnethercote.github.io/2022/10/27/how-to-speed-up-the-rust-compiler-in-october-2022.html)
still applies.

## Notable improvements

[#124129](https://github.com/rust-lang/rust/pull/124129): In this PR, [Rémy
Rakic](https://github.com/lqd/) made lld the default linker for the nightly
compiler on x86-64/Linux. lld is much faster than the system linkers, and this
change reduced the wall-time for several benchmark results by 30% or more. The
idea of using lld first [came up in
2017](https://github.com/rust-lang/rust/issues/39915) and took a surprising
amount of time and effort to get into a shippable state; many thanks to Rémy
for getting it over the line. You can enable lld on other configurations by
following [these
instructions](https://nnethercote.github.io/perf-book/build-configuration.html#linking).
Manual enabling has been possible for a long time, but defaults matter and it's
good to get wider exposure for this feature. Read more in the [announcement
blog
post](https://blog.rust-lang.org/2024/05/17/enabling-rust-lld-on-linux.html).
Work is underway to enable lld on stable releases.

[#133807](https://github.com/rust-lang/rust/pull/133807): In this PR, [Kajetan
Puchalski](https://github.com/mrkajetanp) enabled PGO for ARM64/Linux, giving
10-20% speedups across pretty much all benchmarks on that platform. Great work!

[#127513](https://github.com/rust-lang/rust/pull/127513),
[#135763](https://github.com/rust-lang/rust/pull/135763): In these PRs, [Nikita
Popov](https://github.com/nikic) upgraded the LLVM version used by the compiler
to LLVM 19 and then LLVM 20. These PRs gave a mean wall-time reduction across
all benchmarks results of
[1.33%](https://perf.rust-lang.org/compare.html?start=e552c168c72c95dc28950a9aae8ed7030199aa0d&end=0b5eb7ba7bd796fb39c8bb6acd9ef6c140f28b65&stat=instructions%3Au&nonRelevant=true)
and
[0.78%](https://perf.rust-lang.org/compare.html?start=2162e9d4b18525e4eb542fed9985921276512d7c&end=ce36a966c79e109dabeef7a47fe68e5294c6d71e&stat=instructions%3Au&nonRelevant=true).
Every LLVM major update for several years has made the Rust compiler faster.
This is not due to some law of nature. Rather, it reflects sustained, excellent
work from the LLVM developers. Kudos to them.

[#132566](https://github.com/rust-lang/rust/pull/132566): In this PR, [Ben
Kimock](https://github.com/saethlin) made a hard-to-describe change to how
monomorphization works. If we look just at incremental builds that involve code
generation, it gave a mean wall-time reduction across all benchmark results of
[5.00%](https://perf.rust-lang.org/compare.html?start=5afd5ad29c014de69bea61d028a1ce832ed75a75&end=ee4a56e353dc3ddfcb12df5fe2dc1329a315c2f5&stat=wall-time&check=false&full=false&incrFull=false&doc=false&nonRelevant=true&showRawData=true),
with a handful exceeding 20%. These results are somewhat inflated by an
artifact of how the benchmarks are measured (see the PR description for
details) and in practice the real improvements were probably between half and
two-thirds of what was measured. Still a very impressive improvement for a
single change.

[#136771](https://github.com/rust-lang/rust/pull/136771): In this PR,
[scottmcm](https://github.com/scottmcm) simplified `slice::Iter::next` enough
that it can be inlined. This resulted in a mean cycle reduction across all
benchmark results of
[0.34%](https://perf.rust-lang.org/compare.html?start=28b83ee59698ae069f5355b8e03f976406f410f5&end=f04bbc60f8c353ee5ba0677bc583ac4a88b2c180&stat=cycles%3Au&nonRelevant=true).
This change is likely to slightly speed up a lot of other Rust programs as
well, because slice iteration is extremely common.

[#133793](https://github.com/rust-lang/rust/pull/133793/commits): The Rust
compiler has excellent error messages, but sometimes this comes at a
performance cost. You may have seen syntax errors that look like this:
```
error: expected one of `:`, `@` or `|`, found `,`
```
To generate these, the parser maintained a vector of tokens called
`expected_token_types` that was constantly updated. The compiler's token type
is more heavyweight than you might expect. It does not implement `Copy` and so
the token pushing requires calls to `clone` and the clearing requires calls to
`drop`. (I'm nearing the end of a [long-term project to fix
this](https://github.com/rust-lang/rust/pull/124141).) In this PR I changed
this vector to use a simpler type which made the pushing and clearing much
cheaper. This gave icount wins across many benchmarks, the best being 2.5%.

[#131481](https://github.com/rust-lang/rust/pull/131481): I previously wrote
about this PR of mine in a [post about dataflow
analysis](https://nnethercote.github.io/2024/12/19/streamlined-dataflow-analysis-code-in-rustc.html).
It was a small performance win, giving sub-1% instruction count reductions on a
few benchmarks. But it was interesting because it involved *removing* a
supposed optimization that was actually a pessimization in practice. Removing
it made the code shorter (500+ lines of code removed). I don't know if this
"optimization" was always a pessimization. Perhaps it was once a speed win but
that changed over time as other things around it changed. It's a good reminder
that writing high performance code isn't easy, and it's always good to keep
measuring things.

## Startup

There were also some improvements relating to startup.

[#131634](https://github.com/rust-lang/rust/pull/131634): In this PR [David
Lattimore](https://github.com/davidlattimore) used protected visibility for
symbols when building `rustc_driver`. This is an arcane symbol/linker thing I
won't pretend to understand that somehow shaves about 10-12 million
instructions off startup, on Linux at least. For a `check` build of "hello
world" that was a 31% icount reduction! 

[#137586](https://github.com/rust-lang/rust/pull/137586): This is a funny one.
When profiling very short running compilations, e.g. a `check` build of "hello
world", the single hottest function was something in LLVM called
`SetImpliedBits`. It accounted for almost 20% of the ~26 million instructions
executed. This function is used when checking LLVM's support for code
generation features, such as SSE2, AVX, etc. On x86 and x86-64 CPUS there are
60+ such features that need to be checked. Each one requires the Rust compiler
to call into LLVM, and the code on the LLVM side is very, uh, sub-optimal.
Furthermore, I discovered that the Rust compiler was actually checking every
feature twice, once when considering stable features and once when considering
both stable and unstable features. In this PR I eliminated this second check
for each feature, which gave almost 10% icount reductions in the best case.
This benefit should be seen on x86 and x86-64 across all operating systems. On
other architectures it will be smaller because they have fewer features to
check.

[LLVM #130936](https://github.com/llvm/llvm-project/pull/130936): Nikita Popov
made a related change to fix the sub-optimal ("implemented in a really stupid
fashion") feature checking within LLVM. When the next LLVM major update happens
we should see another ~10% icount win for "hello world", and `SetImpliedBits`
will no longer confuse people by clogging up Cachegrind profiles of these
short-running compiler invocations. 

The wall-time improvements of all these startup changes are likely in the order
of a few milliseconds, which is too small to measure reliably. There are two
ways to look at this. The pessimistic view is to observe that it's well below
what a human would notice. The optimistic view is to note that these
milliseconds are shaved off every single invocation of the compiler, and this
can only be a good thing. I choose the latter.

## General Progress

For the period 2024-03-04 to 2025-03-17 we had some reasonably good overall
performance results.

First,
[wall-time](https://perf.rust-lang.org/compare.html?start=50e77f133f8eb1f745e05681163a0143d6c4dd7d&stat=wall-time&showRawData=true&nonRelevant=true&tab=compile&end=8279176ccdfd4eebd40a671f75b6d3024ae56b42):
- There were 526 results measured across 43 benchmarks.
- 306 of these were improvements, and 220 were regressions. The mean change was
  a reduction of 6.37%. Plenty of the reductions were in the double digits,
  some exceeding 50%. Most of the regressions were in the single digits.

Next, [peak memory
usage](https://perf.rust-lang.org/compare.html?start=50e77f133f8eb1f745e05681163a0143d6c4dd7d&stat=max-rss&showRawData=true&nonRelevant=true&tab=compile&end=8279176ccdfd4eebd40a671f75b6d3024ae56b42):
- Again, there were 526 results measured across 43 benchmarks.
- 149 of these were improvements, and 377 were regressions. The mean change was
  a 2.87% increase, and most of the changes were in the single digits.

Finally, [binary
size](https://perf.rust-lang.org/compare.html?start=50e77f133f8eb1f745e05681163a0143d6c4dd7d&stat=size%3Alinked_artifact&tab=compile&end=8279176ccdfd4eebd40a671f75b6d3024ae56b42&nonRelevant=true&showRawData=true):
- There were 324 results measured across 43 benchmarks.
- 178 of these were improvements, and 146 were regressions. The mean change was
  a 1.95% reduction, and most of the changes were in the single digits.
- If we restrict things to [non-incremental release
  builds](https://perf.rust-lang.org/compare.html?start=50e77f133f8eb1f745e05681163a0143d6c4dd7d&stat=size%3Alinked_artifact&tab=compile&end=8279176ccdfd4eebd40a671f75b6d3024ae56b42&nonRelevant=true&showRawData=true&debug=false&check=false&doc=false&incrUnchanged=false&incrFull=false&incrPatched=false),
  which is the most interesting case for binary size, there were 17
  improvements, 26 regressions, and the mean change was a reduction of 0.10%.

For all three metrics, all but a handful of results met the significance
threshold. I haven't bothered separating those results because they made little
difference to the headline numbers. As always, these measurements are done on
Linux.

In short, speed generally improved; memory usage regressed a small amount,
probably not enough to be noticeable; and binary size didn't change much. 

Over the past year I have not spent that much time on compiler performance. For
the rest of this year I hope to change that by working on both incremental
compilation and parallelism in the front end. These are areas of the compiler
that are complex, but have potential for significant speed improvements.

One final thing: we will be [updating the rustc-perf benchmark
suite](https://github.com/rust-lang/rustc-perf/issues/2024) soon, as per
policy, because it has been three years since the last update. This will mostly
consist of updating the real-world crate benchmarks (e.g. `serde`) to their
latest versions. This is to ensure we are benchmarking representative code.

