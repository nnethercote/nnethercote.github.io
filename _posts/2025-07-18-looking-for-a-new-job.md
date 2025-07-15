---
layout: post
title: I am a Rust compiler engineer looking for a new job
---

For the past 3.75 years I have been fortunate to work on Futurewei's Rust team,
where I had enormous freedom to "make Rust better" however I see fit. It has
been the highlight of my career and I am grateful to Sid Askary and other
Futurewei folks that helped make it happen.

Unfortunately, this job is going away soon; the team is being shrunk due to
budget cuts. I don't have insight into the detailed reasoning, but I suspect it
mostly comes down to two things: (a) international politics and economics are
in upheaval, and (b) AI is sucking up a lot of money and attention in the tech
world, leaving less for everything else.

I would love to find a position that lets me continue to work on Rust in this
fashion. Rust is an incredible project and technology. It needs and deserves to
have people who are paid full-time to maintain it, and I believe I am a good
person to do this.

## Some numbers

It's hard to quantify impact, but let's give it a try. All numbers are correct
at the time of writing.

First, let's start with commits to the [rust-lang/rust
repository](https://github.com/rust-lang/rust/).
- `git log` says I have made 3,375 commits.
- 560 were from 2016-2020, during my time at Mozilla, where I found ways to
  contribute to Rust part-time despite not being on the Rust team.
- 2,815 were since I joined the Futurewei team in late 2021.
- This puts me at #16 on the [all-time contributors
  list](https://github.com/rust-lang/rust/graphs/contributors), which goes back
  to 2010. It's #14 if you exclude the #1 and #2 entries which are for a bot
  and a person that do a large number of merge commits.
- The contributors list includes people who haven't been active for years. If
  we restrict it to the last two I am at #6, or #4 after excluding merge commits.
  (This time window can be selected via a drop-down menu at the top right of
  the [contributors
  list](https://github.com/rust-lang/rust/graphs/contributors), though it
  doesn't produce a usable link.)

Next, let's expand consideration to [GitHub
contributions](https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-github-profile/managing-contribution-settings-on-your-profile/viewing-contributions-on-your-profile),
which includes (non-merge?) commits and also things like issue creation,
reviews, and discussions.
- I am currently the #16 contributor, with [4013
  contributions](https://thanks.rust-lang.org/rust/all-time/), or #15 if we exclude
  [@bors](https://github.com/bors) the bot.
- I don't know where I ranked when I started at Futurewei, but I would estimate
  slightly outside the top 100.
- My contribution rate has ticked up over time, and I have been in the top five
  human contributors to several Rust releases.

Commits and contributions are imperfect measures of impact, for sure. But when
the numbers get high enough, I think they provide a decent signal. The other
names at the top of these lists are all highly valuable and prolific project
members.

## Areas of expertise

I was a "compiler contributor" for a long time, which was the designation used
for the second tier of contributors, in comparison to the first tier in the
"compiler team".

Last year things were reorganised and I am now a ["compiler team
member"](https://forge.rust-lang.org/compiler/membership.html?highlight=maintainer#compiler-team-member)
("someone who contributes regularly") and also a
["maintainer"](https://forge.rust-lang.org/compiler/membership.html?highlight=maintainer#maintainers)
("not only a regular contributor, but are actively helping to shape the
direction of the team or some part of the compiler (or multiple parts)")

I am a member of the primary reviewers group.

I am also a member of the [compiler performance working
area](https://www.rust-lang.org/governance/teams/compiler#team-wg-compiler-performance)
and the [parallel rustc working
area](https://www.rust-lang.org/governance/teams/compiler#team-wg-parallel-rustc).

In terms of the compiler codebase:
- The compiler is over 700,000 lines of code, in the `compiler/` directory of
  the Rust repository.
- I have laid eyes on almost every file in `compiler/`.
- I have committed changes to 75 of the 77 crates in `compiler/`.

Some compiler areas where I have particular depth of expertise include the
following.
- Compiler performance, profiling and benchmarking
- Lexing and parsing
- Token/AST representation and processing, including macro expansion
- Builtin macro code generation
- Compiler error generation
- Dataflow analysis structure
- CGU splitting

I have also made major contributions to
[rustc-perf](https://github.com/rust-lang/rustc-perf/), smaller contributions
to rustdoc, clippy, rustfmt, and cargo, and a handful of contributions to
external projects like [quote](https://github.com/dtolnay/quote),
[Bevy](https://github.com/bevyengine/bevy),
[cargo-fuzz](https://github.com/rust-fuzz/cargo-fuzz),
[cargo-llvm-lines](https://github.com/dtolnay/cargo-llvm-lines), [The Little
Book of Rust Macros](https://lukaswirth.dev/tlborm/),
[thin-vec](https://github.com/Gankra/thin-vec),
[rust-smallvec](https://github.com/servo/rust-smallvec), and
[c2rust](https://github.com/immunant/c2rust/).

## Specific contributions

In the Rust community I'm best known for working on compiler performance, and
in the past 3.75 years I've done a lot of work there. Some highlights:
- I oversaw the [compiler performance roadmap in
  2022](https://hackmd.io/YJQSj_nLSZWl2sbI84R1qA).
- I [analyzed](https://hackmd.io/mxdn4U58Su-UQXwzOHpHag?view) the compiler's
  performance on the most popular 1000 crates, and made a number of speedups as
  a result.
- I [overhauled declarative macro
  expansion](https://nnethercote.github.io/2022/04/12/how-to-speed-up-the-rust-compiler-in-april-2022.html),
  giving big speed wins and also making the code simpler and more maintainable.
- I [optimized the code generated for `derive`d traits such as
  `Debug`](https://nnethercote.github.io/2022/07/20/how-to-speed-up-the-rust-compiler-in-july-2022.html), reducing compile times.
- I implemented a new flag [-Zmacro-stats](https://nnethercote.github.io/2025/06/26/how-much-code-does-that-proc-macro-generate.html)
  to measure proc macro code size and then [shrank the size of Bevy's
  `#[derive(Reflect)]` code](https://github.com/bevyengine/bevy/issues/19873).
  This reduced the `cargo check` time for the `bevy_ui` crate by 50%!
- I helped with the rustc-perf benchmark suite updates in
  [2022](https://hackmd.io/d9uE7qgtTWKDLivy0uoVQw) and
  [2025](https://github.com/rust-lang/rustc-perf/issues/2024).
- I [overhauled Cachegrind's annotation
  tools](https://nnethercote.github.io/2023/05/03/valgrind-3.21-is-out.html) to
  make them more useful for profiling the Rust compiler and other complex
  programs.
- I continued writing my long-running ["How to speed up the Rust
  compiler"](https://nnethercote.github.io/2025/05/22/how-to-speed-up-the-rust-compiler-in-may-2025.html)
  blog series, with another dozen posts.
- There are far too many individual PRs to mention, but three of my favourites
  were: [`ChunkedBitSet`](https://github.com/rust-lang/rust/pull/93984) and the
  removal of [`HybridBitSet`](https://github.com/rust-lang/rust/pull/133431);
  [deep `fast_reject](https://github.com/rust-lang/rust/pull/97345) (with
  [@lcnr](https://github.com/lcnr)); and a [surprisingly massive rustdoc
  speedup](https://github.com/rust-lang/rust/pull/141421).

I also branched out and did a lot of non-performance work. A lot of this can be
classified as "maintainability" or "cleanup" or "refactoring" or "tech debt
removal". I have a knack for it and in a codebase as large and old as the Rust
compiler it is always valuable. Some examples:
- I overhauled the internal APIs for generating compiler errors, which are used
  all over the compiler and were a mess, via 30+ PRs and hundreds of commits.
  My favourite review comment was [this
  one](https://github.com/rust-lang/rust/pull/119606#issuecomment-1880642866):

  > Thanks for finally making `emit` consume. You broke the "add 1 to this counter
  if you tried" situation.

  I.e. I fixed a problem that multiple other people had previously tried and
  failed to fix. It only took a PR with 14 commits that touched 112 files.
- I greatly [simplified the structure of the dataflow analysis
  passes](https://nnethercote.github.io/2024/12/19/streamlined-dataflow-analysis-code-in-rustc.html).
- I [removed an awful internal design detail whereby AST nodes could be
  embedded in tokens](https://github.com/rust-lang/rust/pull/124141). I
  completed this three years after I first tried, on the third attempt, after a
  great number of preliminary cleanups.
- I removed [save-analysis](https://github.com/rust-lang/rust/pull/101841) and
  [compiler plugins](https://github.com/rust-lang/rust/pull/116412), two
  compiler features that had been deprecated for years but needed someone to
  push through their removal. These removals then enabled various subsequent
  simplifications.
- I overhauled and simplified how [codegen unit splitting
  works](https://nnethercote.github.io/2023/07/11/back-end-parallelism-in-the-rust-compiler.html)
  in the compiler backend.
- I [turned on `use` item formatting within the
  compiler](https://github.com/rust-lang/rust/pull/125443), a surprisingly
  controversial change. The PR modified 1,867 files, which is my biggest single
  PR. I am very happy to no longer have to think how to format `use` items.
- I simplified compiler/rustdoc startup in a few ways, e.g.
  one example is [here](https://github.com/rust-lang/rust/pull/102769).
- I [fixed a ton of inconsistencies in operator representation in 
  tokens and the
  AST](https://github.com/rust-lang/compiler-team/issues/831).
- I [fixed a lot of places where the empty symbol was misleading used to mean
  "no symbol"](https://github.com/rust-lang/rust/issues/137978), fixing some
  bugs along the way. (This is Rust, not C, we have the `Option` type.)
- I [got rid of the ancient `P` type in the
  AST](https://github.com/rust-lang/rust/pull/141603). It was a smart pointer
  type that predated Rust 1.0, and I replaced it with `Box`.

If I run the following command that summarizes my changes on the repository:
```
git log --author="Nicholas Nethercote" -p | diffstat
```
the output is this:
```
8759 files changed, 145338 insertions(+), 152183 deletions(-)
```
[Negative lines of
code!](https://www.folklore.org/Negative_2000_Lines_Of_Code.html) Nice.
Fittingly, by far the most common first word in my commit messages is "Remove",
used on 752 of 3,375 commits.

## Other activities

Most of my work is around code, but I have also done some other things over the
past 3.75 years.
- I gave talks at [RustNL 2023](https://www.youtube.com/watch?v=q2vJ8Faundw),
  [GOSIM
  2023](https://www.youtube.com/watch?v=gcd2Lqd4Ln0&list=PLx2fLm_Sb4FGJNZHrG4nv0le-Ouu1O18I),
  and [GOSIM 2024](https://www.youtube.com/watch?v=8E7I0EGRXo0). 
- I attended RustConf 2022 and RustWeek 2025 and the co-located unconferences
  for project members. RustWeek 2025 was especially good, I met and reconnected
  with a lot of people and I returned home feeling newly energized. (Which
  makes my losing my job shortly afterward all the more disappointing.)
- I have done a small amount of Rust performance consulting work for ISRG and
  OpenAI.
- I maintained [The Rust Performance
  Book](https://nnethercote.github.io/perf-book/).
- I did all this while working 100% remotely in Melbourne, Australia, something
  I've done since 2009, sometimes as a contractor, sometimes as an employee.

## On the job market

In short: I do a lot of work on Rust. I think it's valuable. I'd love to be
able to keep doing it. If you know of any way that could happen, please get in
touch.

I have worked in the industry for almost twenty years. I have worked for
Mozilla and Apple. I have a [PhD in
Valgrind](https://nnethercote.github.io/pubs/phd2004.pdf) and other
[publications](https://nnethercote.github.io/pubs.html). I co-won the [Most
Influential PLDI Paper Award](https://www.sigplan.org/Awards/PLDI/) in 2017.

If I can't find a job that involves me working on Rust, I would like to find a
job that uses Rust for interesting ends, preferably in ways that are open
source.

I am **not** interested in any of the following:
- blockchain/cryptocurrencies
- generative AI
- algorithmic trading
- relocating from Melbourne

My contact details and other basic information is
[here](https://nnethercote.github.io/about-me.html). My LinkedIn profile is
[here](https://www.linkedin.com/in/nnethercote/). Thank you for reading this
far!
