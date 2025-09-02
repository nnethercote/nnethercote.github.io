---
layout: post
title: Faster Rust builds on Mac
---

Did you know that macOS has a secret setting that can make Rust builds faster?
It can also make Rust tests faster. It probably even has similar effects for
other compiled languages such as C, C++, Go, and Swift. It sounds crazy, but
read on...

## The problem 

Isaac Asimov reportedly said: *the most exciting phrase to hear in science...
is not "Eureka" but "that's funny..."*

I noticed something recently while looking at the output of `cargo build
--timings` on Mac: build scripts took a strangely long time to execute.
Consider the following output from compiling
[wild](https://github.com/davidlattimore/wild) on my 2019 MacBook Pro.

<p align="center">
  <img src="/images/2025/09/04/before.png" width=300>
</p>

Time is on the x-axis. Each blue/purple bar is a single invocation of the
compiler. Each orange bar measures the time taken to execute a build script.
And the orange bars are quite long.

[Build scripts](https://doc.rust-lang.org/cargo/reference/build-scripts.html)
let you do custom tasks that fall outside the normal Cargo workflow. Sometimes
they are expected to be slow, such as when invoking a C compiler to build a
library. But often they are trivial. A common case is to run `rustc --version`
to see what version of the compiler is installed and then adjust some
configuration detail accordingly.

All the build scripts shown in this output are simple ones that should be very
quick to run, and that's what I saw when I measured on Linux. So why were they
taking between 0.48 and 3.88 seconds on Mac? And why was each successive one
slower than the previous?

I tried running a couple of these build scripts directly instead of via Cargo.
They were much faster that way, e.g. 75ms vs. 300ms. Weird. At first I
suspected that Cargo was mismeasuring the build script executions somehow. I
looked at the relevant code in Cargo but it was pretty straightforward and
seemed unlikely to be hiding a problem.

## The explanation

Before digging further I
[asked](https://rust-lang.zulipchat.com/#narrow/channel/246057-t-cargo/topic/build.20scripts.20slow.20on.20macOS.3F/near/535948902)
on Zulip if this behaviour was familiar to anyone. [Weihang
Lo](https://github.com/weihanglo) suggested it might be caused by code-signing
verification or some other security check.

Wait, what? This was not the answer I was expecting, but it was correct. macOS
has an antivirus feature called
[XProtect](https://support.apple.com/en-gb/guide/security/sec469d47bd8/web).

> XProtect checks for known malicious content whenever:
> - An app is first launched
> - An app has been changed (in the file system)
> - XProtect signatures are updated

In other words, the OS scans every executable for malware on the first run.
This makes sense for executables downloaded from the internet. It's arguably
less sensible for executables you compiled yourself. Indeed, build scripts are
the worst possible case for this kind of check, performance-wise, because each
build script executable is typically run exactly once.

(XProtect is closely related to another security feature called
[Gatekeeper](https://support.apple.com/en-au/guide/security/sec5599b66df/web).
As I understand it, Gatekeeper verifies signed code while XProtect does generic
malware scans. Note that people often use the name "Gatekeeper" when referring
to all of these activities.)

## The workaround

You can avoid these scans by adding Terminal (or any alternative terminal app
you are using, such as iTerm) as a "developer tool" in System Settings. See
[these docs](https://nexte.st/docs/installation/macos/#gatekeeper) for details.
Note: as the docs say, you will likely need to restart Terminal for the change
to take effect. But if you want to undo the change, you might need to reboot
the machine for the change to take effect.

This is the "secret setting" I mentioned at the start of this post. Searching
around, I found only a few online mentions of it.
- A [blog post](https://donatstudios.com/mac-terminal-run-unsigned-binaries).
- A [users.rust-lang.org
  post](https://users.rust-lang.org/t/cargo-run-slow-on-macos-when-binary-already-built/117450/6).
- A [Hacker News comment](https://news.ycombinator.com/item?id=24394150).
- The [cargo-nextest docs](https://nexte.st/docs/installation/macos/#gatekeeper), which cite the Hacker News comment.
- The [Zed docs](https://zed.dev/docs/development/macos#speeding-up-verification), which cite the cargo-nextest docs.
- [Corrode's Tips for Faster Rust Compile
  Times](https://corrode.dev/blog/tips-for-faster-rust-compile-times/#macos-only-exclude-rust-compilations-from-gatekeeper),
  which cites the cargo-nextest docs *and* the Zed docs! (This post is an
  excellent and comprehensive collection of tips for speeding up Rust
  compilation, by the way.)
- A [rust-lang Zulip
  thread](https://rust-lang.zulipchat.com/#narrow/channel/182449-t-compiler.2Fhelp/topic/.E2.9C.94.20Is.20there.20any.20performance.20issue.20for.20MacOS.3F/near/340013849).

Please note that if you do this you are disabling an OS security feature. You
should not do it unless you are comfortable with the potential speed/security
trade-off.

## The benefits: cargo build, cargo check

The following image replicates the `cargo build --timings` output from above
alongside the output from a run with XProtect disabled.

<p align="center">
  <img src="/images/2025/09/04/before.png" width=300>
  <img src="/images/2025/09/04/after.png" width=300>
</p>

A huge difference! Those orange bars are now tiny. The build scripts are taking
around 0.06 to 0.14 seconds each on my old MacBook Pro.

This definitely has the potential to speed up full builds of various Rust
projects. In this case, the original wild build took 25.9s and the new one took
25.0s. I didn't do careful measurements to see if those numbers were
consistent. The exact effect will depend heavily on a project's dependency
graph and the characteristics of your machine, but if build script execution is
on the critical path it will certainly have an effect.

Great! But maybe you don't actually run build scripts all that often. Most of
the time you're just rebuilding your own code, not third-party dependencies,
other than after the occasional `cargo clean`, right? Well...

## The benefits: cargo run

If your project is an executable, you'll be paying the XProtect cost every
single time you rebuild and rerun. It's extra time on every edit-compile-run
cycle. Yuk.

## The benefits: cargo test

Disabling XProtect also helps for test binaries. Especially pre-2024-edition
doctests, where [every doctest gets its own
binary](https://doc.rust-lang.org/edition-guide/rust-2024/rustdoc-doctests.html)!
And the `cargo-nextest` folks clearly noticed it.

The exact effect will depend on the structure of the tests. The Rust compiler
itself provides a compelling example. Its most comprehensive test suite is
called `tests/ui/` and involves running almost 4,000 individual executables,
most of them tiny. [Mads Marquart](https://github.com/madsmtm) found that
disabling XProtect reduced the runtime of this test suite [from 9m42s to
3m33s](https://rust-lang.zulipchat.com/#narrow/channel/246057-t-cargo/topic/build.20scripts.20slow.20on.20macOS.3F/near/536314094)! Incredible.

## The benefits: other languages

I haven't tested this, but developers using other compiled languages will
presumably benefit similarly, so long as development involves frequent
compilation and execution of binaries.

## Spreading the joy

The status quo is that this behaviour is documented in a few obscure places and
99%+ of Mac users are unaware. Fortunately, Mads has a [draft
PR](https://github.com/rust-lang/cargo/pull/15908) for Cargo that detects if
XProtect is enabled and issues a warning to the user explaining its impact and
how to disable it. (There is apparently no programmatic way to disable XProtect
in the terminal and we wouldn't want to do that anyway; the user should
be required to make an active choice.)

The PR is worth a look because it has a precise description of the situation,
one that goes into more detail than I have here. Also, it answers a question
posed much earlier in this post: in the original `cargo build --timings`
output, why was each successive build script slower than the previous? The PR
has the answer:

> the XprotectService daemon runs in a single thread, so if you try to launch
> 10 new binaries at once, the slowdown will be more than a second.

On my old MacBook Pro, which has eight cores, it's much more than a second.
Going back to my original `cargo build --timings` run, the final build script
took 3.88s to run. Its execution overlapped with that of most of the previous
build scripts. Most of that 3.88s is actually spent waiting for the daemon.
Good grief.

There will need to be careful discussion and review of how the warning is
presented to the user, given that it's about disabling an OS security feature.
But I am happy there is a clear path forward to get this knowledge out of "deep
lore" territory and into the purview of normal users. In the meantime, if you are
a Mac user you could consider disabling XProtect in the terminal and get the
speed benefits immediately.
