---
layout: post
title: How to speed up the Rust compiler in May 2025
---

It has been two months since my [last
post](https://nnethercote.github.io/2025/03/19/how-to-speed-up-the-rust-compiler-in-march-2025.html)
on the Rust compiler's performance. Time for a small update.

## Benchmarks updated

This update comes hot on the heels of the previous one because
[Jakub Beránek](https://github.com/Kobzol/) and I
[updated](https://github.com/rust-lang/rustc-perf/issues/2024) most of the
"primary" benchmarks in the [rustc-perf benchmark
suite](https://github.com/rust-lang/rustc-perf/tree/master/collector/compile-benchmarks).
These benchmarks are verbatim copies of third-party crates, and we have a
[policy](https://github.com/rust-lang/rustc-perf/tree/master/collector/compile-benchmarks#benchmark-update-policy)
of updating them every three years to ensure we are measuring code that people
are using. This does impact data continuity, though we do have a set of old
"stable" benchmarks that never change, plus "secondary" benchmarks (e.g.
microbenchmarks) that rarely change.

## General Progress

For the period 2025-03-17 to 2025-05-20 you can see the results on the primary
metrics here:
[wall-time](
https://perf.rust-lang.org/compare.html?start=8279176ccdfd4eebd40a671f75b6d3024ae56b42&stat=wall-time&showRawData=true&tab=compile&end=2b96ddca1272960623e41829439df8dae82d20af&nonRelevant=true),
[peak memory
usage](https://perf.rust-lang.org/compare.html?start=8279176ccdfd4eebd40a671f75b6d3024ae56b42&stat=max-rss&showRawData=true&tab=compile&end=2b96ddca1272960623e41829439df8dae82d20af&nonRelevant=true),
and [binary
size](https://perf.rust-lang.org/compare.html?start=8279176ccdfd4eebd40a671f75b6d3024ae56b42&stat=size%3Alinked_artifact&showRawData=true&tab=compile&end=2b96ddca1272960623e41829439df8dae82d20af&nonRelevant=true).
I won't go in to detail because none of them changed that much. This is a good
thing! Because of the benchmarks update we only had 25 benchmarks (mostly
secondary benchmarks) measured across the period, instead of the usual 43. My
next update will include all the new benchmarks.

## One notable improvement

[#140561](https://github.com/rust-lang/rust/pull/140561): In this PR,
[Michael Goulet](https://github.com/compiler-errors) made a fairly small change
to how local variables are gathered by the type checker, making the gathering
lazier. This gave an impressive 10%+ reduction in compile times for certain
`check` builds of the `cranelift-codegen-0.119.0` benchmark, because it made
obligation processing faster. I don't really understand the effect, but it does
make me wonder if there is some kind of custom profiling/logging we could do to
identify sub-optimal obligation processing.
