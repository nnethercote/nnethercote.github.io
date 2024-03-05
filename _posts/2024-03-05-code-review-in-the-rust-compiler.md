---
layout: post
title: "Code review in the Rust compiler"
---

I recently joined the general code review rotation for the Rust compiler, which
increased the number of reviews I do. This post describes my experience, and
contains some thoughts about reviewing in general.

## Rust project code reviews

Like many software projects, Rust uses code reviews. Every change occurs
through a GitHub pull request (PR), and every PR must be reviewed and approved
by someone with review authority before being merged. In this post I will focus
on the compiler, but code review is also used for the standard library, Cargo,
and other Rust tools.

There are currently 15 [Compiler
team](https://www.rust-lang.org/governance/teams/compiler#Compiler%20team)
members (who are "developing and managing compiler internals and
optimizations"), and another 28 [Compiler team
contributors](https://www.rust-lang.org/governance/teams/compiler#Compiler%20team%20contributors)
(who are "contributing to the Rust compiler on a regular basis"). All of these
people have review authority for any compiler PR, but in practice people only
review PRs that are within their area of expertise. To gain membership of one
of these groups requires invitation after an extended period of productive
contribution to the compiler, so we trust all reviewers to be sensible.

Anyone who creates a PR can choose a reviewer for it by including `r?
@username` in the PR description. This is appropriate if you know who an
appropriate reviewer is. But much of the time no reviewer is requested, and
rustbot will auto-assign a reviewer after consulting the
[`triagebot.toml`](https://github.com/rust-lang/rust/blob/master/triagebot.toml)
file, which has machine-readable details about available reviewers.

A subset of the Compiler team members and contributors have opted in to
auto-assignment, and rustbot chooses a reviewer randomly from this group. At
the time of writing, [14 people](
https://github.com/rust-lang/rust/blob/516b6162a2ea8e66678c09e8243ebd83e4b8eeea/triagebot.toml#L651-L668)
have opted in to the general rotation, which means they can be assigned reviews
for any compiler PR. And some other team members and contributors have opted in
to review only certain parts of the compiler.

For more details, see the [Review
policies](https://forge.rust-lang.org/compiler/reviews.html) page on Rust
Forge.

## My reviewing experience

I have been a Compiler team contributor for several years, and have thus had
review authority for that time. In 2022 I [opted
in](https://github.com/rust-lang/highfive/pull/429) to review assignment in a
couple of compiler components that I understood well. But the number of
auto-assigned reviews I received was small, perhaps one a month. I also
sometimes received explicit review requests by name, perhaps two weeks or so.

Late last year I started thinking about joining the general review rotation.
Partly because I create a [lot of
PRs](https://thanks.rust-lang.org/rust/1.76.0/), and partly because I've been
working on the compiler for quite some time.

I was hesitant, because the compiler is a big piece of software. There are a
few parts I know extremely well, more parts that I know moderately well, but
also large swathes I know almost nothing about. But that description is true
for almost all compiler developers, and doing more reviews might force me to
learn about new parts of the compiler, which would be good. After a discussion
among compiler developers about reviewing load and burnout concerns, on January
22 I took the plunge and [joined the general
rotation](https://github.com/rust-lang/rust/pull/120212).

Since then my experience been very positive. First of all, the review load is
less than I expected. I recorded my review load for 32 days covering the period
from January 22 to February 22.
- Nineteen reviews were auto-assigned to me.
  - Thirteen of these I did without problem.
  - Two were "stolen", i.e. someone else reviewed and approved the PR before I
    even saw it. (Because I was asleep! Three cheers for multi-timezone
    projects.)
  - One was half-stolen, where someone else reviewed it without giving final
    approval it, and I ended up rubber-stamping the final version.
  - One I immediately manually reassigned because it was clearly outside my area of
    expertise.
  - One was immediately reassigned to another reviewer by the creator, probably
    because they simply forgot to manually assign at creation.
  - [One](https://github.com/rust-lang/rust/pull/120718) I would have
    reassigned, but two others reviewers had already requested reassignment
    (which had taken 10 days), so I decided to review it even though it was
    outside my comfort zone, and I ultimately approved it.
- Six reviews were manually assigned to me.
  - Five of these I did myself.
  - One was stolen before I saw it.

<!--
-----------------------------------------------------------------------------
rustc review diary, early 2024
-----------------------------------------------------------------------------
#120212: I signed up for more reviews. Merged on 23/1/2024

-----------------------------------------------------------------------------
random assignment
-----------------------------------------------------------------------------
summary
- 32 days from 22/1/2024 to 22/2/2024
- 19 auto-assigned
  - 14 I did
  - 2 stolen
  - 1 half-stolen
  - 1 immediately manually reassigned
  - 1 I reassigned
  - 1 I would have reassigned, but didn't
- 6 manually assigned
  - 1 stolen

-----------------------------------------------------------------------------

22/1/2024 Don't make statement nonterminals match pattern nonterminals #120221 

24/1/2024 Deduplicate more sized errors on call exprs #120293 

25/1/2024 Remove coroutine info when building coroutine drop body #120330 

28/1/2024 Move UI issue tests to subdirectories #120439 

1/2/2024 add test for try-block-in-match-arm #120540 
- quasi-stolen by compiler-errors

2/2/2024 Stop bailing out from compilation just because there were incoherent
traits #120558 
- I passed it on to lcnr

3/2/2024 For a rigid projection, recursively look at the self type's item
bounds to fix the associated_type_bounds feature #120584 
- compiler-errors immediately reassigned to lcnr

6/2/2024 Update E0716.md for clarity #120684 

7/2/2024 Don't expect early-bound region to be local when reporting errors in
RPITIT well-formedness #120707

8/2/2024 improve pretty printing for associated items in trait objects #120739 
- stolen by compiler-errors

8/2/2024 Provide more suggestions on invalid equality where bounds #120751 
- quasi-stolen by compiler-errors

10/2/2024 Turn the "no saved object file in work product" ICE into a
translatable fatal error #120865

16/2/2024 Fix closure kind docs #121141 

17/2/2024 Add "algebraic" fast-math intrinsics, based on fast-math ops that
cannot return poison #120718 
- outside my comfort zone, did it anyway because it had already been bounced
  around reviewers

19/2/2024 add test for panicking attribute macros #121275 

20/2/2024 Add docs for extension proc-macro #121304

22/2/2024 Fix typo in serialized.rs #121401 

22/2/2024 Improve error messages for generics with default parameters #121416 

22/2/2024 Move as many tests from tests/ui/numbers-arithmetic to tests/ui/lint
as possible #121432 

-----------------------------------------------------------------------------
non-random assignment
-----------------------------------------------------------------------------
Remove various has_errors or err_count uses #120342 
- 26/1/2024: oli-obk assigned to me

Account for unbounded type param receiver in suggestions #120396 
- 27/1/2024: compiler-errors reassigned to me

Remove a bunch of `has_errors` checks that have no meaningful or the wrong
effect (PR #120531
- 1/2/2024: oli-obk assigned to me, estebank stole it overnight

rustc_monomorphize: fix outdated comment in partition #120602 
- 3/2/2024: klensy assigned to me

Add parallel rustc ui tests #120664
- 6/2/2024: mw asked for reassignment, Sparrow chose me

errors: only eagerly translate subdiagnostics #121085 
- 15/2/2024: davidtwco assigned to me
-->

Overall, the load was less than I expected. I had feared getting two or three
auto-assigned reviews per day, but it was only 0.59 reviews per day, or 0.53 if
you exclude the stolen ones where I didn't have to do anything. My joining
increased the general rotation number from eight to nine, but since then more
people have joined or rejoined and the number is now fourteen, which will have
reduced the load.

The reviews were easier than I expected. Most were fairly small and only took a
few minutes. The [smallest](https://github.com/rust-lang/rust/pull/121401)
fixed a single spelling mistake in a comment (changing "accomodate" to
"accommodate"). I also reassigned fewer reviews than I expected. Maybe my
knowledge of the compiler is better than I thought, or maybe many auto-assigned
reviews don't require highly specific knowledge.

The only stressful part of the experience was on the last day of this recording
period, when I got three auto-assigned reviews in a single day, which was
coincidentally a day in which I was dealing with multiple reported panics from
a PR I had merged the day before. I guess it was just bad luck that I got a
cluster of review requests on a busy day. Perhaps the auto-assignment could be
adjusted to avoid this kind of clustering.

## How I do reviews

When rustbot auto-assigns a PR to a reviewer, it says the following, about the
assigned reviewer: "They will have a look at your PR within the next two weeks
and either review your PR or reassign to another reviewer."

Two weeks is a long time. This period is chosen because some reviewers have
limited time available to work on Rust. I'm fortunate enough to be paid to work
full-time on Rust, so I aim to complete all my reviews within one business day.
(If a review request arrives on Friday afternoon, I probably won't get to it
until Monday morning.) I appreciate fast reviews, so I try to return in kind.
["Do unto others"](https://en.wikipedia.org/wiki/Golden_Rule).

I often ask questions in reviews, rather than making definitive statements.
Things like "would it make sense to do X here instead of Y?" Or even just "why
is this done like this?" The answers are often enlightening, and I often ask
for the answers to be added to the code as comments.

I try to be positive, with a "does this make things better overall" mindset. I
wouldn't accept a PR with genuine problems, but not every nitpick is always
necessary. And it's rare that a PR is so flawed that it is outright rejected,
without any chance of merging after some changes. I also try to give
encouraging remarks when asking for changes, like "looks good overall, just a
couple of minor things to fix".

I try to include at least a few words when I approve a PR, even just "nice
change", because sometimes a bare `r+` can be hard to interpret, and might
leave the author wondering "did he think this was an excellent change, or good,
or just ok?"

## How I code for reviews

When I write code I always have the future reviewer in mind, and I try to make
their task as easy as possible. Most of my PRs have multiple commits, and are
designed to be reviewed one commit at a time. I use [atomic
commits](https://www.aleksandrhovhannisyan.com/blog/atomic-git-commits/)
heavily, so that most commits don't have unrelated changes in them, and I aim
for every commit to build and pass tests. I use `git rebase -i` frequently to
support the above. I will often split a commit into multiple smaller commits
after finishing it. As well as helping the reviewer, all this helps if a
problem is found after merging, because bisecting a bug or crash down to a
small commit is much nicer than a big commit that does multiple things.

I try to write descriptive commit messages that include both the "what" and the
"why". A common form is "The current code does X, which is suboptimal for
reason Y. This commit changes the code to instead do Z, which fixes the
problem." Likewise for PR descriptions.

I manually pick reviewers most of the time, rather than letting rustbot
auto-assign for me. This is because I often know who is an appropriate reviewer
for the PR. I also tend to overselect from a subset of reviewers that I know
are usually fast at reviewing. (As the saying goes, "no good deed goes
unpunished".) But I especially don't want to be auto-assigned someone who is not
appropriate, who might then take a week to get to the review and then reassign
it; that's not a good use of anyone's time. This approach of mine probably
skews review loads, but those fast reviewers are typically people paid to work
full-time on Rust, which makes me feel a little less guilty.

## The value of reviews

I'm a strong believer in the importance of code reviews. They're a fundamental
quality mechanism, and they spread knowledge of the code base. They also
provide a layer of defense against various kinds of malfeasance. I have worked
on
[projects](https://nnethercote.github.io/2023/05/03/valgrind-3.21-is-out.html)
that don't require reviews, and the ability to push any change with only post
hoc oversight feels sketchy.

I know that waiting for reviews and performing reviews can be annoying. My boss
used an analogy: "coding is like cooking, and reviewing is like washing the
dishes". Like all analogies, it'll break if you stretch it too far, but there
is some truth there: the dishes always need doing.

There are genuine risks of burnout if people have to do too many reviews. I
think the compiler team is in a good state right now, and better than a couple
of months ago, but some other Rust teams (e.g. standard library and Cargo) are
struggling due to fewer reviewers being available. (And standard library API
reviews require a lot of time and care.) **Update:** Nilstrieb [pointed
out](https://mas.to/@nilstrieb@hachyderm.io/112041518618584105) that the
standard library reviewing situation has improved recently.

When people discuss reviewing challenges, they often look to technical or
process solutions. I am a bit skeptical about these. There may be room for some
improvement, but ultimately there's a certain amount of labour that needs doing
by people, and a smarter assignment process won't change that. There is no
substitute for having a healthy number of reviewers. (And no, I don't see
anything that might be labelled as "AI" having any positive effect here.)
Having said that, I will say that Rust is a fantastic language to review code
in, because of its readability, and safety guarantees, and the wide use of
`rustfmt`.

So I'm happy to be sharing more of the Rust compiler reviewing load.

## Coda

[The only valid measurement of code quality:
WTFs/minute](https://www.osnews.com/story/19266/wtfsm/).
