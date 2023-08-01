---
layout: post
title: "How to speed up the Rust compiler: data analysis assistance requested!"
---

**Update**: see the [follow-up
post](https://nnethercote.github.io/2023/08/01/how-to-speed-up-the-rust-compiler-data-analysis-update.html) for responses and updated data sets.

Are you good at data analysis techniques such as linear regression? Want to
help speed up the Rust compiler?

## Back-end parallelism in rustc

Two weeks ago I [wrote about my recent
attempts](https://nnethercote.github.io/2023/07/11/back-end-parallelism-in-the-rust-compiler.html)
to speed up the Rust compiler by making changes to the parallel back-end. These
attempts were mostly unsuccessful.

The back-end splits the generated MIR code into codegen units (CGUs) and then
uses LLVM to generate machine code, using one thread per CGU. The CGU splitting
algorithm attempts to split the code into evenly sized CGUs, which requires
estimating how long LLVM will take to compile each CGU. Estimating this
accurately is difficult. The current estimation function is basic and often
understimates or overestimates significantly, which can hurt compile times.

Among the
[feedback](https://www.reddit.com/r/rust/comments/14wcezs/backend_parallelism_in_the_rust_compiler/)
I received on my last post were numerous suggestions to use data analysis
techniques to improve the estimation function. This is not my area of
expertise, so I am asking for help.

At the end of this post I have links to several data sets, each of which
records a number of per-CGU measurements from compiling the
[rustc-perf](https://github.com/rust-lang/rustc-perf/) benchmarks. These data
sets include numerous inputs (independent variables) that measure static code
size, such as the number of functions, number of MIR statements, etc. They also
include several outputs (dependent variables) which are timings related to the
back-end's execution. It's only a few hundred lines of data in total.

I tried doing some basic analysis myself using
[scikit-learn](https://scikit-learn.org/). It was useful to some extent because
(a) I learned a bit about linear regression, and (b) it made me think carefully
about which measurements I should collect. The final data set I have is better
than what I started with. But I didn't get much in the way of practical
results. In fact, it felt like I got completely different results every time I
made small changes to what I was measuring.

## A request for help

Hopefully people with expertise in data analysis can do a better job! Let me
explain what I'm looking for.

- A better estimation function than the one we currently have.
- And one that makes the compiler faster than it currently is. It is not
  guaranteed that a better estimation function will have that effect. I've come
  up with a couple that were better as measured statistically, but didn't
  improve compile speed, or even made it slightly worse. The CGU scheduling
  effects are very unpredictable, and you can't assume that an estimation
  function that is a few percent better will make the compiler faster. Having
  said that, my hope is that a sufficiently large improvement would translate
  to actual speed-ups.
- It is better for the estimation function to overestimate how long a CGU will
  take to compile, rather than underestimate. That is because underestimates
  can lead to "long pole" CGUs that can serialize execution.
- The absolute values computed by the estimation function do not matter. Only
  relative values matter. Think of the function as producing an abstract,
  unit-less measure of time rather than a concrete measure of time such as
  milliseconds.
- I am quite concerned about overfitting. These data sets are from a single
  machine, but rustc runs on many different machines, with a wide range of
  architectures and microarchitectures.
- These data sets are also from a single version of rustc, using a single
  version of LLVM. I am concerned about the possibility of accuracy drift over
  time.
- I would prefer an estimation function that isn't too complex and is
  comprehensible. The current function is very simple, in most cases just
  adding the number of basic blocks and statements. Something a bit more
  complex is fine, but I don't want some function with a dozen inputs and
  coefficients like `[0.866544, 0.381334e-02, 1.779101e-01, ...]`. I also don't
  want negative coefficients because I don't think they make sense in this
  context; I can't think of a program feature where you could make compilation
  faster by adding more of them. Also, a zero-sized CGU should be estimated as
  taking something very close to zero time.
- I know of one definite problem with the existing estimation function, which
  is that counting MIR statements can be very inaccurate if you don't consider
  their internals. In particular, single MIR statements can get very large. The
  MIR for the `deep-vector` stress test includes one statement defining a
  vector literal with over 100,000 elements. Unsurprisingly, the current
  estimation function badly underestimates how long this benchmark takes to
  compile. So the data sets contain measurements of things inside MIR
  statements (such as places and rvalues) that capture this kind of detail.

I hope these requirements are reasonable.

Here are the data sets:
- [Debug build, primary benchmarks](/aux/2023/07/25/Debug-Primary.txt)
- [Opt build, primary benchmarks](/aux/2023/07/25/Opt-Primary.txt)
- [Debug build, secondary benchmarks](/aux/2023/07/25/Debug-Secondary.txt)
- [Opt build, secondary benchmarks](/aux/2023/07/25/Opt-Secondary.txt)

The primary benchmarks are representiative of real-world Rust code. They are
more important than the secondary benchmarks, which include stress tests,
microbenchmarks, and other forms of less realistic code.

I have annotated each file with an explanation of what the columns mean. I hope
this is enough for others to do useful analysis. Please let me know via
[Reddit](https://www.reddit.com/r/rust/comments/158tcel/how_to_speed_up_the_rust_compiler_data_analysis/)
or
[Zulip](https://rust-lang.zulipchat.com/#narrow/stream/247081-t-compiler.2Fperformance/topic/CGU.20size.20estimation.20function)
if anything is unclear. I can also re-run the data gathering if necessary, e.g.
to measure additional things.

And [here](/aux/2023/07/25/lin.py) is the simple Python script I was using for
my analysis, in case that's of interest.

Here's to hoping that crowdsourcing the data analysis will lead to good results
for all Rust users!
