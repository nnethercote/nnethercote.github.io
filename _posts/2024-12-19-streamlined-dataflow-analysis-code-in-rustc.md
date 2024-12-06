---
layout: post
title: Streamlined dataflow analysis code in rustc
---

Sometimes I pick a crate in the Rust compiler and read through its code to
learn about it and find things that I can improve. Often the improvements
are small, but sometimes they snowball.

One example involved the `rustc_errors` crate. rustc is famous for its high
quality error messages. These messages can be long and sophisticated, with
multiple parts. The internal APIs for constructing and emitting errors are
complex, and had accumulated for years without anybody stepping back and
considering them as a whole. When I did that, it led to a couple of months of
detangling, across more than 30 pull requests and hundreds of commits. I hacked
through code duplication, naming inconsistencies, excessive abstraction,
unnecessary complexity, and some plain old weirdness. Errors are emitted from
thousands of places in the compiler, at every compilation stage, so these
improvements made a lot of code nicer and easier to understand. A full
description of this work would make for the world's dullest blog post, so
instead I will write about a more interesting example.

<p align="center">
  <img title='"Cat with yarn" by AriTheHorse is licensed under CC BY-SA 4.0. To view a copy of this license, visit https://creativecommons.org/licenses/by-sa/4.0/?ref=openverse.'
  alt="A ginger cat stares at the camera, with yarn spread haphazardly across the floor nearby"
  src="/images/2024/12/19/cat-with-yarn.jpg" width=500>
</p>

`rustc_mir_dataflow` is a crate that defines a framework for forward and
backward [dataflow
analysis](https://rustc-dev-guide.rust-lang.org/mir/dataflow.html) on
[MIR](https://rustc-dev-guide.rust-lang.org/mir/index.html), and contains more
than a dozen analyses implemented within that framework. These analyses
determine things like the program points where variables are live, or have been
initialized, or are borrowed. The analysis results are used in various parts of
the compiler such as the borrow checker. The crate is reasonably complex and
understanding it requires some knowledge of dataflow analysis concepts.
Fortunately, due to a misspent youth I am familiar with terms such as
*lattice*, *partially-ordered set*, *top*, *bottom*, *least upper bound*,
*greatest lower bound*, *lub*, *glb*, *join*, and *meet*. I even know which of
these are just different names for the same thing.

## My changes

Let's look at the 17 pull requests (PRs) I made for this crate.

### [#118203](https://github.com/rust-lang/rust/pull/118203) Minor `rustc_mir_dataflow` cleanups

- 16 commits
- -95 lines of code

This was a typical first cleanup PR, with all the commits just rounding off
small rough edges. Eleven of them had a commit message starting with the word
"Remove".

<p align="center">
  <img title='"IMG_6560" by adrigu is licensed under CC BY 2.0. To view a copy of this license, visit https://creativecommons.org/licenses/by/2.0/?ref=openverse.'
  alt="A tabby cat sleeps with its head resting against a small ball of blue yarn"
  src="/images/2024/12/19/img-6560.jpg" width=500>
</p>

### [#118230](https://github.com/rust-lang/rust/pull/118230) Streamline MIR dataflow cursors

- 9 commits
- -130 lines of code
- 3 types and 2 traits removed

When a dataflow analysis runs it produces a "results" value, and the results
can be inspected with a "results cursor". For example, you can answer questions
like "was variable `x` initialized at the end of this basic block?"

There were two results types (`Results` and `ResultsCloned`) and three results
cursor types (`ResultsCursor`, `ResultsClonedCursor`, and `ResultsRefCursor`).
You can tell from the names that they were all similar but optimized for
different ownership scenarios. But these different scenarios weren't material.

This PR removed `ResultsCloned`, `ResultsClonedCursor`, and `ResultsRefCursor`,
leaving just `Results` and `ResultsCursor`, both of which lost a type
parameter. The PR also removed a trait called `CloneAnalysis` that was
basically a complicated synonym for `Copy`, and another trait called
`AnalysisResults` that isn't worth explaining. The resulting code was shorter
and simpler (though slightly clunky in a couple of places, which we will return
to later) and there was no performance penalty.

<p align="center">
  <img title='"April 19 - Did I Do That?" by iowa_spirit_walker is licensed under CC BY 2.0. To view a copy of this license, visit https://creativecommons.org/licenses/by/2.0/?ref=openverse.'
  alt="A grey cat lies on carpet, looking at the camera, with strands of blue yarn spread across the floor around it"
  src="/images/2024/12/19/did-i-do-that.jpg" width=500>
</p>

### [#118638](https://github.com/rust-lang/rust/pull/118638) More `rustc_mir_dataflow` cleanups

- 4 commits
- -36 lines of code
- 1 type and 1 macro removed

The first commit in this PR removed unused arguments from some functions.

The second commit removed a macro `impl_visitable!` that existed to avoid some
repetitive boilerplate code. But the macro had a single use and was complex
enough that writing the boilerplate code by hand took fewer lines of code and
was much easier to read. A tiny bit of code duplication is often better than a
bad abstraction. (The boilerplate code ended up being removed later on anyway.)

The third commit involved a generic type `BorrowckAnalyses<B, U, E>` that was
used to implement two concrete typedefs `BorrowckResults` and
`BorrowckFlowState`. The commit removed `BorrowckAnalyses` and replaced the two
typedefs with concrete types. Again, a tiny bit of boilerplate code was shorter
and simpler than the more abstract, repetition-free version.

The fourth commit made a tiny change to two methods in the `GenKillAnalysis`
trait. Not a big deal, but that trait would soon see a lot more action.

<p align="center">
  <img title='"Boron tired of string" by John Leach is licensed under CC BY 2.0. To view a copy of this license, visit https://creativecommons.org/licenses/by/2.0/?ref=openverse.'
  alt="A black cat reclines on a bed with a strand of yellow yarn over its head and shoulders"
  src="/images/2024/12/19/boron-tired.jpg" width=500>
</p>

### [#131481](https://github.com/rust-lang/rust/pull/131481) Remove `GenKillAnalysis`

- 7 commits
- -496 lines of code
- 2 traits and 1 type removed

This PR is my favourite.

There were two kinds of dataflow analysis in the compiler, each represented by
a trait: `Analysis`, which is the basic kind, and `GenKillAnalysis`, which is a
more specialized kind for [*gen-kill
analyses*](https://en.wikipedia.org/wiki/Data-flow_analysis#Bit_vector_problems).
`GenKillAnalysis` was similar to `Analysis` but had some minor differences, and
there was a blanket implementation of `Analysis` such that any type
implementing `GenKillAnalysis` would automatically implement `Analysis`. There
was some duplication of function across the two traits and the whole setup had
triggered my spidey senses for some time. I had previously made a couple of
failed attempts to make the two traits share more code.

Eventually I realized that `GenKillAnalysis` was just an optimized way to run
a gen-kill analysis which involved precomputing a transfer function for each
basic block that would then reduce the amount of work done later on. But a
gen-kill analysis could also be run using `Analysis`. So I tried doing that
with all the gen-kill analyses, curious to see what the performance regression
would be. Oh! It turned out to be a small performance *improvement*. Not big
wins, mostly sub-1% improvements in instruction counts, but it was consistent
across the benchmark suite. The supposed optimization was actually a
pessimization.

So this PR removed `GenKillAnalysis`, the `GenKillSet` type, and merged the
`AnalysisDomain` trait into `Analysis`. These simplifications set up some
subsequent improvements, such as the next PR.

<p align="center">
  <img title='"Cat jumping" by barbourians is licensed under CC BY-SA 2.0. To view a copy of this license, visit https://creativecommons.org/licenses/by-sa/2.0/?ref=openverse.'
  alt="A small grey kitten leaps energetically at a strand of dangling yarn"
  src="/images/2024/12/19/cat-jumping.jpg" width=500>
</p>


### [#132338](https://github.com/rust-lang/rust/pull/132338) Remove `Engine`

- 2 commits
- -66 lines of code
- 1 type removed

To run an analysis implementing the `Analysis` trait you had to call the
`into_engine` method which would create an `Engine` value. Then you could
optionally give it a pass name, and finally you called `iterate_to_fixpoint` to
perform the analysis and produce results. Like this:
```
let results = MyAnalysis
    .into_engine(tcx, body)
    .pass_name("my")
    .iterate_to_fixpoint();
```
With `GenKillAnalysis` gone, `Engine` was reduced to a builder type with a
single modifier method, `pass_name`. This PR removed `into_engine` and `Engine`
by simply giving `iterate_to_fixpoint` an extra `Option<&'static str>` argument
holding the optional name. To run an analysis now looks like this:
```
let results = MyAnalysis.iterate_to_fixpoint(tcx, body, Some("my"));
```
Simpler and less plumbing all around.

<p align="center">
  <img title='"080415 moxie and yarn" by Dan4th is licensed under CC BY 2.0. To view a copy of this license, visit https://creativecommons.org/licenses/by/2.0/?ref=openverse.'
  alt="A black cat lies on a wooden floor, a strand of yarn under its front paws"
  src="/images/2024/12/19/moxie-and-yarn.jpg" width=500>
</p>

### [#132346](https://github.com/rust-lang/rust/pull/132346) Some graphviz tweaks 

- 3 commits
- +5 lines of code

This PR was just some minor improvements to the machinery for generating graphviz
visualizations of dataflow analysis results.

<p align="center">
  <img title='"Fiona_6wks_toy" by Linda N. is licensed under CC BY 2.0. To view a copy of this license, visit https://creativecommons.org/licenses/by/2.0/?ref=openverse.'
  alt="A kitten lies on a bed with a small knitted yarn ball right beside its head"
  src="/images/2024/12/19/fiona-6wks-toy.jpg" width=500>
</p>

### [#132347](https://github.com/rust-lang/rust/pull/132347) Remove `ValueAnalysis` and `ValueAnalysisWrapper`. 

- 2 commits
- -193 lines of code
- 1 module, 1 trait, and 1 type removed

There was a module called `value_analysis` with a trait called `ValueAnalysis`
and a struct called `ValueAnalysisWrapper` that implemented the `Analysis`
trait. This infrastructure served a single dataflow analysis called
`ConstAnalysis`, which implemented the `ValueAnalysis` trait. No other dataflow
analysis needed (or will need) to do value analysis. Which means this
infrastructure was a great deal of unnecessary indirection and abstraction.

This PR removed `value_analysis`, `ValueAnalysis`, and `ValueAnalysisWrapper`,
and moved their functional parts directly into `ConstAnalysis`, making the
relevant code much shorter and easier to read.

<p align="center">
  <img title='"Yarn 1" by Sarah_Jones is licensed under CC BY-SA 2.0. To view a copy of this license, visit https://creativecommons.org/licenses/by-sa/2.0/?ref=openverse.'
  alt="A grey cat lies on grey carpet, with a tangle of dark blue yarn under its front paws"
  src="/images/2024/12/19/yarn-1.jpg" width=500>
</p>

### [#132134](https://github.com/rust-lang/rust/pull/132134) Remove `ResultsVisitable` 

- 2 commits
- -13 lines of code
- 1 trait and 1 type removed, 1 type added

Most analysis uses followed a pattern of "compute the analysis results, then
visit them", but there was one exception. For borrow checking we ran three
separate analyses (`Borrows`, `MaybeUninitializedPlaces`, and
`EverInitializedPlaces`), combined them into a single `BorrowckResults`, and
only then visited that combined `BorrowckResults`. `BorrowckResults` was just
different enough from a normal `Results` that it required the existence of a
`ResultsVisitable` trait to abstract over the visiting differences. Each of
`Results` and `BorrowckResults` implemented that trait.

The first commit in this PR introduced `Borrowck` and bundled the three borrow
check analysis results into a standard `Results<Borrowck>` instead of the
exceptional `BorrowckResults`. Once that was done, these results could be
visited like any other analysis results, and `BorrowckResults` was removed.

That meant `Results` was the only impl of `ResultsVisitable`, and that trait
could be removed. This removed unnecessary layers of indirection, abstraction,
and generic types in several places.

<p align="center">
  <img title='""Koshka with Yarn" by WATERBOYsh is licensed under CC BY 2.0. To view a copy of this license, visit https://creativecommons.org/licenses/by/2.0/?ref=openverse.'
  alt="A black cat lies on carpet with a ball of reddish yarn nearby, one strand of which loops over the top of its head"
  src="/images/2024/12/19/koshka-with-yarn.jpg" width=500>
</p>

### [#133155](https://github.com/rust-lang/rust/pull/133155) Yet more `rustc_mir_dataflow` cleanups 

- 5 commits
- +29 lines of code

This cleverly-named PR did a few things.
- It merged two functions that were always called together.
- It added some comments explaining non-obvious aspects of the dataflow
  analysis framework that had taken me some time to work out.
- It made it possible for a `ResultsCursor` to either own or borrow a
  `Results`, which fixed the slightly clunky code added above in #118230.
- And a couple of other minor improvements.

<p align="center">
  <img title='"7 September" by carolyn.will is licensed under CC BY 2.0. To view a copy of this license, visit https://creativecommons.org/licenses/by/2.0/?ref=openverse.'
  alt="A ginger and white kitten lies looking at the camera with a loop of blue yarn over its front right paw"
  src="/images/2024/12/19/7-september.jpg" width=500>
</p>

### [#133326](https://github.com/rust-lang/rust/pull/133326) Remove the `DefinitelyInitializedPlaces` analysis. 

- 1 commit
- -345 lines of code
- 2 types and 1 trait removed

There were four different dataflow analyses relating to the initialization of
variables and places: `MaybeInitializedPlaces`, `MaybeUninitializedPlaces`,
`DefinitelyInitializedPlaces`, and `EverInitializedPlaces`. As it happens,
`DefinitelyInitializedPlaces` is just the inverse of
`MaybeUninitializedPlaces`, was not meaningfully used, and had some minor bugs.
So this PR removed it.

This also allowed the removal of two things that were only needed for that
analysis: the `MeetSemiLattice` trait (which was implemented by six types:
`bool`, `IndexVec`, `BitSet`, `ChunkedBitSet`, `Dual`, and `FlatSet`) and the
`Dual` type (which implemented four traits: `DebugWithContext`,
`JoinSemiLattice`, `MeetSemiLattice`, and `GenKill`).

<p align="center">
  <img title='"Yarn attack" by Birdies100 is licensed under CC BY-SA 2.0. To view a copy of this license, visit https://creativecommons.org/licenses/by-sa/2.0/?ref=openverse.'
  alt="A black and white cat lies on carpet with a tangle of white yarn spread across its face and front paws"
  src="/images/2024/12/19/yarn-attack.jpg" width=500>
</p>

### [#133475](https://github.com/rust-lang/rust/pull/133475) `MaybeStorage` improvements 

- 4 commits
- -9 lines of code

This PR made some small improvements, none of which were notable.

<p align="center">
  <img title='"hm, we liked the ball of yarn better" by lemonhalf is licensed under CC BY-SA 2.0. To view a copy of this license, visit https://creativecommons.org/licenses/by-sa/2.0/?ref=openverse.'
  alt="Two cats sitting on a bed stare impassively at a besocked foot on the end of a human leg that is only shown up to the knee" 
  src="/images/2024/12/19/hm-we-liked.jpg" width=500>
</p>

### [#133431](https://github.com/rust-lang/rust/pull/133431) Remove `HybridBitSet`

- 9 commits
- -731 lines of code
- 3 types removed

This PR removed the most lines of code.

All the gen-kill analyses use bitsets to hold analysis results. The naive space
cost is roughly *O(m × n)* because a function has multiple things such as local
variables to track (*m* bits per bitset), and multiple program points at which
they are tracked (*n* bitsets), and *m* and *n* increase roughly linearly as
function size increases. For programs with large functions, this can results in
tens or hundreds of megabytes of bitsets if you aren't careful.

In 2018 [I introduced a hybrid bitset](
https://blog.mozilla.org/nnethercote/2018/11/06/how-to-speed-up-the-rust-compiler-in-2018-nll-edition/)
type into rustc, which gave huge reductions in peak memory use for the then-new
NLL borrow checker. This type, later renamed `HybridBitSet`, would switch from
a sparse representation to a dense representation once the number of set bits
exceeded a small number (8). This was a good fit for rustc's dataflow analysis
needs at the time. However, `HybridBitSet` was later eclipsed by another type,
`ChunkedBitSet`, that I introduced in 2022. `ChunkedBitSet` can use a mix of
dense and sparse representation for different sections of a single bitset, and
replaced some of the `HybridBitSet` uses. Also, the removal of
`GenKillAnalysis` above removed more `HybridBitSet` uses.

This PR replaced the few remaining `HybridBitSet` uses with `ChunkedBitSet` and
`BitSet` (which has a simple, dense representation) and removed `HybridBitSet`.
It also removed `HybridBitIter` and an underlying type called `SparseBitSet`.
To avoid a performance hit, I had to improve the `ChunkedBitSet` iterator,
which had been implemented in a simple but slow fashion.

<p align="center">
  <img title='"so...exhausted...defeated by...yarn" by reegmo is licensed under CC BY-SA 2.0. To view a copy of this license, visit https://creativecommons.org/licenses/by-sa/2.0/?ref=openverse.'
  alt="A black and white cat lies on its side an orange carpet, with a tangle of dark yarn across its flank"
  src="/images/2024/12/19/so-exhausted.jpg" width=500>
</p>

### [#133328](https://github.com/rust-lang/rust/pull/133328) Simplify `SwitchInt` handling 

- 5 commits
- -68 lines of code
- Removed 1 trait, 2 types, a closure, and added 1 type

The code for handling switches (used to implement `match`) had some complicated
control flow, involving an "applier" type implementing a particular trait, and
a closure that was passed to a method of the applier and called on each
outgoing switch edge. For the masochists out there, full details are in the
[relevant commit
message](https://github.com/rust-lang/rust/pull/133328/commits/4d8316f4d40cc9fb431b9cab5825c32fac43a19a).
In short, I found a way to simplify things, removing the trait and the closure.

I then tried a follow-up optimization attempt that was impossible before this
refactoring and quite simple afterwards. That optimization attempt ended up
failing, but it was a good way to prove that the new code is simpler.

<p align="center">
  <img title='"Yarn attack 2" by Birdies100 is licensed under CC BY-SA 2.0. To view a copy of this license, visit https://creativecommons.org/licenses/by-sa/2.0/?ref=openverse.'
  alt="A black and white cat lies on its side on carpet and grabs tightly at a ball of white yarn"
  src="/images/2024/12/19/yarn-attack-2.jpg" width=500>
</p>

### [#133891](https://github.com/rust-lang/rust/pull/133891) Introduce `MixedBitSet`

- 6 commits
- +178 lines of code
- 2 types added

The aforementioned `ChunkedBitSet` is good at minimizing memory usage when
compiling programs with huge functions where dataflow bitsets have large domain
sizes. But it's heavyweight for small functions with small bitsets, because any
non-empty ChunkedBitSet takes at least 256 bytes of memory.

This PR introduced `MixedBitSet`, a bitset that uses `BitSet` for
small-to-medium bitsets and `ChunkedBitSet` for large bitsets. It gave moderate
speed and memory usage wins, and it's a lot simpler than the removed
`HybridBitSet`.

<p align="center">
  <img title='"Fat cat" by Elsie esq. is licensed under CC BY 2.0. To view a copy of this license, visit https://creativecommons.org/licenses/by/2.0/?ref=openverse.'
  alt="A fat tabby cat sprawls against a wall"
  src="/images/2024/12/19/fat-cat.jpg" width=500>
</p>


### [#133938](https://github.com/rust-lang/rust/pull/133938) `rustc_mir_dataflow` cleanups, including some renamings 

- 9 commits
- -62 lines of code

This PR renamed a bunch of things (variables, types, and methods) for greater
consistency. It also removed some unused trait impls and bounds.

<p align="center">
  <img title='"IMG_4152" by adrigu is licensed under CC BY 2.0. To view a copy of this license, visit https://creativecommons.org/licenses/by/2.0/?ref=openverse.'
  alt="A tiny brown puppy sits in a nest of red yarn and looks directly at the camera"
  src="/images/2024/12/19/img-4152.jpg" width=500>
</p>


### [#134065](https://github.com/rust-lang/rust/pull/134065) Move `write_graphviz_results` 

- 2 commits
- -9 lines of code

This PR just moved a function to a better spot and fixed an out-of-date comment.

<p align="center">
  <img title='"cfor cat chasing string july 09 - weighing just 2.5lbs" by Tim Pearce, Los Gatos is licensed under CC BY 2.0. To view a copy of this license, visit https://creativecommons.org/licenses/by/2.0/?ref=openverse.'
  alt="A white and ginger kitten claws and bites at a strand of red yarn"
  src="/images/2024/12/19/cfor-cat.jpg" width=500>
</p>

### [#134152](https://github.com/rust-lang/rust/pull/134152) Simplify `rustc_mir_dataflow::abs_domain`

- 1 commit
- -26 lines of code

This final PR simplified a trait and an impl of that trait.

<p align="center">
  <img title='"Knitting yarn or kneading yarn? Im about to embark on my first knitting project. See how much this cat cares... #dailycoco #cocothecat #catsofinstagram #yarn #knitting" by jacquib19 is licensed under CC BY 2.0. To view a copy of this license, visit https://creativecommons.org/licenses/by/2.0/?ref=openverse.'
  alt="A tabby cat kneads a tangle of green yarn; a tightly wound cylinder of multicolour yarn sits in the foreground"
  src="/images/2024/12/19/knitting-yarn.jpg" width=500>
</p>

## Summary

In total, these 17 PRs contained 87 commits, and removed 2,067 lines of code,
including 7 traits and around a dozen types. These changes were all to the
`rustc_mir_dataflow` crate, except for some of the bitset changes that were in
the `rustc_index` crate.

The old code had a lot of abstraction. There were many traits, traits bounds,
generic types, and generic functions. Reading it often involved following
control flow across multiple files: "we start at A, which calls B, which calls
C, which calls D, which does the actual work". It's now more concrete, shorter,
simpler, and a little faster.

When I started I didn't know it would go this far. I just kept looking for
little things to improve, over and over, especially the things that annoyed me.
Sometimes clawing at loose strings is worthwhile.

<p align="center">
  <img title='"kitty diptych" by LOLren is licensed under CC BY 2.0. To view a copy of this license, visit https://creativecommons.org/licenses/by/2.0/?ref=openverse.'
  alt="Two similar photos of a cat in the background grabbing at a strand of yarn coming from a red ball of yarn in the foreground"
  src="/images/2024/12/19/kitty-dyptych.jpg" width=500>
</p>
