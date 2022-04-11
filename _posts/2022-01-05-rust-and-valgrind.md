---
layout: post
title: Rust and Valgrind
---

Valgrind is a very useful tool for working with Rust.

This may surprise you. Why would a tool for detecting memory errors be useful
with a memory safe language? Two reasons:
- Valgrind is much more than a tool for detecting memory errors, and
- Rust is not entirely memory safe.

# Valgrind: more than a memory error detector

Valgrind is best known for detecting memory errors in programs written in C and
C++. But it's more than that. It's actually a [generic framework] for building
dynamic binary analysis tools, i.e. tools that analyze ("analysis") your code
at runtime ("dynamic") at the level of compiled code ("binary").

[generic framework]: https://nnethercote.github.io/pubs/valgrind2007.pdf

The most widely used Valgrind tool is called Memcheck. It's the tool that
detects memory errors, and it runs by default. So it's understandable that many
people say "Valgrind" when they really mean "Memcheck". Also, in the early
days, Valgrind wasn't a generic framework, and Memcheck's functionality was
hardwired in.

Other tools that come with Valgrind include the profilers Cachegrind and
Callgrind, the heap profilers DHAT and Massif, and the thread error detectors
Helgrind and DRD. You can run them with Valgrind's `--tool` option.

# Rust: not entirely memory safe

Rust is famous for its memory safety... assuming you avoid `unsafe`. A lot of
the time this is possible, but in certain cases using `unsafe` is unavoidable.

This isn't a bad thing, though, and it's worth remembering while a small
percentage of Rust code has to be unsafe, in C and C++ programs every line of
code is effectively unsafe.

# Rust and Valgrind

The Valgrind tools can be divided into two main categories: the profiling
tools, and the checking tools.

The profiling tools are useful for any Rust programs. I use Cachegrind and DHAT
frequently, Callgrind moderately often, and Massif very occasionally.

The checking tools are potentially useful in the following cases.

- When writing unsafe code that does low-level unsafe operations. For example,
  I was recently experimenting with a `Vec`-like structure and I used Memcheck
  to diagnose multiple crashes along the way.

- When writing unsafe code due to the use of FFI. For example, if a Rust
  program uses a library written in C.

- When you haven't written any unsafe code, but you don't entirely trust some
  third-party crates that you are using. (Or even the standard library!)

- **[Update (Jan 5, 2022)]** Detecting memory leaks. These aren't common in
  Rust, but are possible (e.g. due to cycles in reference counted types) even
  in safe code. They're not considered unsafe because they can't result in
  dangerous crashes or security vulnerabilities.

Memcheck works well in these cases. Helgrind and DRD may also be useful, though
I don't have any personal experience using them this way.

# Minor issues

There are currently some minor issues with using Valgrind on Rust code that
could affect a small fraction of use cases.

**[Update (Apr 12, 2022)] Valgrind 3.19 is now available. It fixes all of
these minor issues.**

#### Missing inline stack frames

Valgrind 3.18 has a bug in its handling of debug info that causes inline frames
to be ignored in Rust stack traces, which reduces the quality of stack traces.
This mostly affects DHAT and Massif, which rely heavily on stack frames, and
also Memcheck to some extent. This bug was
[fixed](https://bugs.kde.org/show_bug.cgi?id=445668) by Mark Wielaard in
November. Valgrind 3.17 and earlier versions don't have this bug.

#### Incomplete v0 symbol demangling

Rust has two symbol mangling schemes. The old "legacy" scheme is the default in
Rust 1.57. The new "v0" scheme, which is turned on with the `-Z
symbol-mangling-version=v0` option, will become the default [at some
point](https://github.com/rust-lang/rust/pull/89917). The v0 scheme is already
used for symbols within rustc itself, and so the following issues are relevant
for rustc developers.

Support for v0 mangling was added to Valgrind 3.18, but unfortunately it wasn't
tested properly and a silly bug meant that the relevant code path isn't
reached. I [fixed](https://bugs.kde.org/show_bug.cgi?id=445184) this in
November.

Even with that fix, a small fraction of v0 symbols still aren't demangled
because the demangling code can't handle suffixes that LLVM adds to some
symbols. Mark Wielaard has [made
progress](https://bugs.kde.org/show_bug.cgi?id=445916) towards handling these.

#### **[Update 2 (Feb 10)]** Warnings when running `cg_diff`

When running `cg_annotate` on files produced by `cg_diff`, the Cachegrind diff tool, you may see warnings like these:
```
Use of uninitialized value $pairs[0] in numeric lt (<) at cg_annotate line 848.
Use of uninitialized value $high in numeric lt (<) at cg_annotate line 859.
```
This is not a Rust-specific issue, and it can happen with profiling programs
written in any language. The warnings are disconcerting but won't affect the
correctness of the produced files. I
[fixed](https://sourceware.org/git/?p=valgrind.git;a=commit;h=8e60cde69e879627e872668b084f1672195990a0)
the problem in December.

#### Building Valgrind from source

If any of the above issues affect you, you might benefit from [building
Valgrind from source](https://valgrind.org/downloads/repository.html),
particularly given that Valgrind releases occur fairly infrequently.
