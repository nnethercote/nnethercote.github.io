---
layout: post
title: How to speed up the Rust compiler in November 2026
---

My first month working on Rust compiler performance for
[Hexcat](https://hexcat.nl/) is over and it's time to see some of what's
happened since my [last
post](https://nnethercote.github.io/2026/09/30/how-to-speed-up-the-rust-compiler-in-september-2026.html).

## Spans

*Spans* are a critical data structure in the Rust compiler. Every AST, HIR, and
MIR node carries a span. Each span has four fields recording the following.
- A source location (`lo` and `hi`). A crate's source files are concatenated
  into a single buffer, and these are indices into that buffer.
- Possibly some hygiene and provenance data (`context`), relevant for macros
  and other things.
- Possibly an extra relative position (`parent`) that is used to minimize the
  compile time impact of small changes to source locations, such as those
  caused by inserting a single line at the start of a file.

Each of the four fields is 32 bits, resulting in 16 bytes of data. But most of
the time these 16 bytes can be compressed into one of three 8-byte inline
formats, and the remaining cases are interned into a global table. This works
by taking advantage of patterns in the data: many source locations have a small
length (i.e. a small difference between `lo` and `hi`); many spans have a zero
context and/or parent, and the non-zero contexts and parents are typically
small integers; parents are only used in incremental builds.

[#163857](https://github.com/rust-lang/rust/pull/163857): In this PR I replace
the old compression scheme with one that is simpler and more efficient. For
incremental builds we now typically intern around 1% of spans compared to
20-40% with the old scheme. (In non-incremental builds we typically intern
fewer than 0.1%.) Also, we can always store the context field inline even in
the interned case, which is useful because we often read the context by itself.
This change reduced instruction counts across many benchmarks, in the best
cases by more than 3%, and the cycle count improvements were even higher.
Incremental builds saw the largest improvements due to less interning.

[#163971](https://github.com/rust-lang/rust/pull/163971): In this PR [Josh
Triplett](https://github.com/joshtriplett) took advantage of the new
representation to micro-optimize a number of span operations. This reduced
instruction counts across many benchmarks, in the best case by more than 2%.

[#164291](https://github.com/rust-lang/rust/pull/164291): In this PR I tried
using a pattern type to give `Span` a niche so that `Option<Span>` would be the
same size as `Span`. It worked but didn't help performance because we don't use
`Option<Span>` much, and it made the code more complicated. So I abandoned it.

[#163628](https://github.com/rust-lang/rust/pull/163628): During metadata
encoding/decoding and stable hashing we typically need to get information
about the same parent span from a hash table over and over. In this PR I put a
single-entry cache in front of that hash table, which avoids the hash table
lookup in most cases. This reduced instruction counts on many benchmarks, in
the best case by more than 4%, mostly benefiting incremental compilation.

## New trait solver

[#163981](https://github.com/rust-lang/rust/pull/163981),
[#164234](https://github.com/rust-lang/rust/pull/164234),
[#165160](https://github.com/rust-lang/rust/pull/165160):
In these three PRs I focused on the compilation time of
[Diesel](https://github.com/diesel-rs/diesel), a crate for which the
in-development new trait solver is slower than the old trait solver. I did
a dozen or so micro-optimizations across the three PRs, such as early returns
on hot paths, avoiding allocations, avoiding some recomputations, and
optimizing some special cases. These reduced the instruction count overhead of
the new solver on a `Check Full` build from 1.49x to 1.16x, and other new
solver benchmarks like `typenum` and `nalgebra` also saw improvements. There is
still more work to be done but this is good progress.

## Miscellaneous

[#164236](https://github.com/rust-lang/rust/pull/164236): In this PR I
rearranged some code to avoid doing some unnecessary work in an early return
case, reducing instruction counts for many benchmarks, in the best case by over
4%.

[#165022](https://github.com/rust-lang/rust/pull/165022): In this PR I removed
the `AttrTokenStream` and `AttrTokenTree` types. These mirrored the
widely-used `TokenStream` and `TokenTree` types but were only used for `cfg`
processing. This change was mostly about making the code simpler, but it also
avoided some token stream conversions, reducing instruction counts on a range
of benchmarks: by 4% on the `deep-vector` stress test, and by less than 1% on
some real world cases.

[#164965](https://github.com/rust-lang/rust/pull/164965): In this PR I avoided
the creation of one type variable per element in literals requiring type
inference like `vec![1, 2, 3, 4]`. This was a huge win (8-12% cycle count
reduction) for the `deep-vector` stress test containing a `vec` literal
with more than 100,000 elements… and didn't help with any other benchmarks.
Sometimes big wins on stress tests translate to smaller wins on real code, and
sometimes they don't. I ended up merging this change anyway because it was very
simple and did improve an error message in one test.

[#164341](https://github.com/rust-lang/rust/pull/164341): In this PR I added
some additional cases to an early return when processing coercions. This
reduced instruction counts across numerous benchmarks, mostly by less than 1%.

[#165112](https://github.com/rust-lang/rust/pull/165112): There is an existing
`trivial_consts` mechanism in the compiler that skips entire passes (including
borrow checking) for trivial consts like `const N: usize = 0`, to reduce
compile times. In this draft PR I have extended this mechanism so it also
avoids building MIR for these consts. In the best case (`libc`) it reduces
instruction counts by up to 6%, but `trivial_consts` is already tricky and
somewhat controversial, so the path forward here is unclear. More details are
in the [Zulip
thread](https://rust-lang.zulipchat.com/#narrow/channel/131828-t-compiler/topic/.60trivial_consts.60.20without.20MIR/with/636155146).

[#164484](https://github.com/rust-lang/rust/pull/164484): In this PR [Takayuki
Maeda](https://github.com/TaKO8Ki) introduced a sparse encoding mechanism for
metadata. This increased instruction counts slightly, but cycle counts and
wall-times were neutral, and more importantly it reduced metadata sizes by up
to 37% and max RSS (peak memory) by up to 7%.

## Hexcatconf

In October I also travelled to Delft to attend
[Hexcatconf](https://hexcat.nl/conf2026/), a small meetup featuring twenty-ish
people from Hexcat, RustNL, and elsewhere. A long trip, but well worth it! It
was great to catch up with some familiar faces, make some new friends, and
learn more about some of the things people are working on. Thank you to Mara
Bos for organizing the event.

## Overall progress

The wall-time measurements for the period 2026-09-28 to 2026-11-02 that meet
the "relevant" threshold can be seen
[here](https://perf.rust-lang.org/compare.html?start=c1070d69382b8d2f2eb65119c738a77d9e324c9e&stat=wall-time&tab=compile&end=ae36fe22c7e590df40ffd53ac25fea35597c3f3d).
It's a sea of green, with improvements on 236 tests across 45 benchmarks, a
number of them being double-digit percentages, and regressions on just four
tests across three benchmarks.

If we expand the selection to include "non-relevant" results (i.e. those below
the variance thresholds) the results are slightly more mixed (599 improvements
vs. 90 regressions) which is to be expected for the relatively short period of
one month. Overall we see a very healthy mean wall-time reduction of 2.85%, and
an even better mean max-RSS (peak memory) reduction of 4.46%. Good news, which
hopefully [will continue](https://github.com/rust-lang/goals/issues/789).

Finally, the instruction count changes [since the start of the
year](https://perf.rust-lang.org/compare.html?start=2026-01-01&stat=instructions%3Au&tab=compile&end=ae36fe22c7e590df40ffd53ac25fea35597c3f3d&nonRelevant=true)
show something remarkable: out of 561 measurements there are 560 improvements
and a single regression, and the second-worst improvement is 3.10%. This
observation came from [Matyáš Racek](https://github.com/panstromek); in fact,
when he mentioned it a few weeks ago every single result was green. It is
fantastic to see the compiler and related tools continually getting faster even
as new features are added to the language and toolchain. Well done to the many
people who have contributed to this achievement. Let's keep going!
