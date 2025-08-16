---
layout: post
title: Speed wins when fuzzing Rust code with `#[derive(Arbitrary)]`
---

If you are using `#[derive(Arbitrary)]` to fuzz your Rust code, update the
Arbitrary crate to v1.4.2 to get some compile time reductions and possibly some
fuzzing speed improvements.

You can update with the command `cargo update -p arbitrary -p
derive_arbitrary`.

## Fuzzing with Arbitrary

The Arbitrary crate is very useful when fuzz testing Rust code. From the
[README](https://github.com/rust-fuzz/arbitrary/blob/main/README.md):

> The `Arbitrary` crate lets you construct arbitrary instances of a type.
> 
> This crate is primarily intended to be combined with a fuzzer like libFuzzer
> and cargo-fuzz or AFL, and to help you turn the raw, untyped byte buffers that
> they produce into well-typed, valid, structured values. This allows you to
> combine structure-aware test case generation with coverage-guided,
> mutation-based fuzzers.

In other words, it defines a trait `Arbitrary` that can be used to convert a
stream of randomized bytes into valid values. Like many good Rust libraries it
uses proc macros to make user's lives easy: you can just stick
`#[derive(Arbitrary)]` on a type and it will automatically generate the
conversion code for you.

## Code size

I was recently using the Rust compiler's new
[`-Zmacro-stats`](https://nnethercote.github.io/2025/06/26/how-much-code-does-that-proc-macro-generate.html)
option on a project that used `#[derive(Arbitrary)]` and saw that the proc
macro was generating a lot of code. Even for a simple struct like `struct
S(u32, u32)` it would generate more than 100 lines of code. In a large project
containing many types marked with `#[derive(Arbitrary)]`, that much code can
add up and cause a lot of work for the compiler.

I used `cargo expand` to inspect the generated code. Annoyingly, only a
fraction of it code was doing the actual conversion of random bytes to valid
values. The rest involved a per-type counter that protects against an [edge
case](https://github.com/rust-fuzz/arbitrary/issues/107) that can cause
infinite recursion on recursive types.

## Improvements

I made three small improvements.

[#227](https://github.com/rust-fuzz/arbitrary/pull/227): In this PR I marked
the per-type counter as `const`, which enables a more efficient thread local
implementation that can avoid lazy initialization and does not need to track
any additional state.

[#228](https://github.com/rust-fuzz/arbitrary/pull/228): The per-type counter
was generated for every type marked with `#[derive(Arbitrary)]`, even ones that
aren't recursive. Why? It's surprisingly hard for a proc macro to tell if a
type is recursive. Proc macros work entirely at the syntactic level, without
access to type information. At that level, any field might lead to type
recursion. (Even builtin types like `u32`? Yes, because it's possible to define
your own type called `u32`. Sigh.) However, there is one family of types that
can never be recursive: fieldless enums like `enum { A, B }`. In this PR I
removed the per-type counter and the corresponding code for all such types. For
an artificial stress test containing 1,000 fieldless enums, this change reduced
compile times by 75%.

[#229](https://github.com/rust-fuzz/arbitrary/pull/229): The code updating the
per-type counter was somewhat repetitive. In this PR I factored out the
repetitiveness, in a way that shouldn't affect runtime speed. For another
artificial stress test containing 1,000 simple structs, the change reduced
compile times by 30-40%.

On a real-world project using Arbitrary these changes reduced incremental
rebuilds from 4.0s to 3.8s, a ~5% reduction. It's possible that the changes
might also increase fuzzing speed, though I haven't measured that and any
effect is probably small.

## You should update, like, now

These are not enormous wins, but hey, updating Rust crates is really easy. You
should update `arbitrary` and `derive_arbitrary` to [version
1.4.2](https://github.com/rust-fuzz/arbitrary/blob/main/CHANGELOG.md#142),
right now. Check `Cargo.lock` to make sure you did it right.

Happy fuzzing!
