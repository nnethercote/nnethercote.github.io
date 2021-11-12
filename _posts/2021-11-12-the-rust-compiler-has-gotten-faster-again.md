---
layout: post
title: The Rust compiler has gotten faster again
---

I [worked on Rust part-time for several years at
Mozilla](https://blog.mozilla.org/nnethercote/2020/09/08/how-to-speed-up-the-rust-compiler-one-last-time/).
During that period I regularly summarized how the compiler's performance had
improved. For example: [2017-11-12 to
2019-07-24](https://blog.mozilla.org/nnethercote/2019/07/25/the-rust-compiler-is-still-getting-faster/).

The last comparison I did was in August 2020. I had a break from working on
Rust from late 2020 until this week, when I became a full-time member of the
Rust team at Futurewei Technologies. I was curious to see how performance had
improved in that time, and the news was good!

From the period [2020-08-05 to
2021-11-11](https://perf.rust-lang.org/compare.html?start=2020-08-05&end=2021-11-11&stat=wall-time),
there were 459 improvements to the results of the compiler benchmark suite and
only 18 regressions, as the following (very long) screenshot shows.

![rustc-perf wall-time 2020-08-05 to 2021-11-11](/images/2021/11/12/rustc-perf-wall-time-2020-08-05-to-2021-11-11.png)

Among the "real" benchmarks (ignoring less-important ones such as artificial
stress tests and `helloworld`), compile times dropped by up to 58%, with most
results in the 10% to 40% range. There were only two regressions of note:
41.69% for `webrender-wrench opt incr-patched: println` and 15.70% for `cargo
check incr-patched: println`.

This is a fantastic result for this 15 month period. panstromek [suggested on
Zulip](https://rust-lang.zulipchat.com/#narrow/stream/247081-t-compiler.2Fperformance/topic/Speedups.20in.20the.20past.2015.20months/near/261102418)
the following reasons for the improvements:

> From what I remember, notable changes were few pathological cases in
> coherence checking, checking of extern functions, enabling PGO for rustc,
> enabling PGO for Clang (IIRC), 2 LLVM bumps, bunch of changes to incremental
> system from cjgillot, improving codegen of builtin derives and bunch more
> that I can't recall now.

Compilers tend to get slower over time unless performance is actively
monitored and improved. Kudos to everyone who contributed to these
improvements, and also to those people on the [Performance Triage
roster](https://github.com/rust-lang/rustc-perf/blob/master/triage/README.md)
who watch for regressions: ecstatic-morse, Mark-Simulacrum, rylev, and
pnkfelix.

**Update:** In case it wasn't clear, this includes the LLVM team. A decent
chunk of the improvements are due to changes within LLVM, which the Rust
compiler uses for its backend.

If you want to see how performance has changed over a longer period, check out
[2019-11-07 to
2021-11-11](https://perf.rust-lang.org/compare.html?start=2018-11-05&end=2021-11-11&stat=wall-time).
(This is the longest period we can easily examine because the data format for
results changed on 2019-11-07.) The results are even better. When looking at
these results, keep in mind the nature of percentages.
- A 50% compile time reduction means the compiler is 2x faster.
- A 75% compile time reduction means the compiler is 4x faster.
- An 80% compile time reduction means the compiler is 5x faster.
- A 90% compiler time reduction means the compiler is 10x faster.
- A 95% compiler time reduction means the compiler is 20x faster.

Let's hope for more improvements in the future!
