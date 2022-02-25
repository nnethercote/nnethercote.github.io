---
layout: post
title: A brutally effective hash function in Rust
---

**Update (Dec 10, 2021):** I have added some extra information worth reading at
the bottom of this post.

**Update (Feb 25, 2022):** And some more.

The Rust compiler uses hash tables heavily, and the choice of hash function
used for these hash tables makes a big difference to the compiler's speed.

By default, Rust hash tables use [Siphash
1-3](https://en.wikipedia.org/wiki/SipHash), a hash function that is high
quality but fairly slow. In contrast, the Rust compiler uses as hash function
called `FxHasher`, which is surprisingly simple yet effective.

# Rust hashing basics

To put a type into a hash table requires computing a hash value for it. The
computation of a hash value of a type in Rust has two parts.

First, there is the
[`Hash`](https://doc.rust-lang.org/std/hash/trait.Hash.html) trait. This
defines how a type should be traversed by the hash function, but does not
specify the hash function itself.

The following example shows how this is implemented for a simple type.
```rust
struct Person {
    name: String,
    phone: u64,
}

impl std::hash::Hash for Person {
    fn hash<H: std::hash::Hasher>(&self, state: &mut H) {
        self.name.hash(state);
        self.phone.hash(state);
    }
}
```
It's quite mechanical: you just call `hash()` on every field. In fact, it's so
mechanical that the compiler can generate the `Hash` impl for you if you
annotate a type with `#[derive(Hash)]`.

Once you get down to scalar types like integers, the second part comes into
play: the [`Hasher`](https://doc.rust-lang.org/std/hash/trait.Hasher.html)
trait, which defines the actual hash function. It works on byte slices, and
possibly also integers.

Putting these together: to hash a value of a type (e.g. in order to insert it
in a hash table), the `Hasher` is created, then the `Hash` implementation calls
into the `Hasher` one or more times, and then the `Hasher`'s `finish()` method
is called to produce the final `u64` value that is the actual hash value used
by the hash table. This is a simplified description but it's enough to give the
basic idea.

# SipHasher13: A typical hash function

Let's look at the [core of the `SipHasher13`
implementation](https://github.com/rust-lang/rust/blob/953f8c8b1f6e98a4da7acd28aab7e88843348a5f/library/core/src/hash/sip.rs).
Here's how the hasher is initialised.
```rust
#[inline]
pub fn new() -> SipHasher13 {
    SipHasher13::new_with_keys(0, 0)
}

#[inline]
fn new_with_keys(key0: u64, key1: u64) -> Hasher<S> {
    let mut state = Hasher {
	k0: key0,
	k1: key1,
	length: 0,
	state: State { v0: 0, v1: 0, v2: 0, v3: 0 },
	tail: 0,
	ntail: 0,
	_marker: PhantomData,
    };
    state.reset();
    state
}

#[inline]
fn reset(&mut self) {
    self.length = 0;
    self.state.v0 = self.k0 ^ 0x736f6d6570736575;
    self.state.v1 = self.k1 ^ 0x646f72616e646f6d;
    self.state.v2 = self.k0 ^ 0x6c7967656e657261;
    self.state.v3 = self.k1 ^ 0x7465646279746573;
    self.ntail = 0;
}
```
Not too complicated, but there are a number of fields and some magic constants.

Next is the code that does the actual hashing. Don't worry too much about the
details here. (Especially given that I've removed comments for brevity). Just
note that it's reasonably complicated, with many arithmetic and bit operations,
multiple conditions, a loop, and a call to another function `S::c_rounds()`
which isn't shown here but does more bit shuffling.

```rust
#[inline]
fn write(&mut self, msg: &[u8]) {
    let length = msg.len();
    self.length += length;
    let mut needed = 0;
    if self.ntail != 0 {
	needed = 8 - self.ntail;
	self.tail |= unsafe { u8to64_le(msg, 0, cmp::min(length, needed)) } << (8 * self.ntail);
	if length < needed {
	    self.ntail += length;
	    return;
	} else {
	    self.state.v3 ^= self.tail;
	    S::c_rounds(&mut self.state);
	    self.state.v0 ^= self.tail;
	    self.ntail = 0;
	}
    }
    let len = length - needed;
    let left = len & 0x7;
    let mut i = needed;
    while i < len - left {
	let mi = unsafe { load_int_le!(msg, i, u64) };
	self.state.v3 ^= mi;
	S::c_rounds(&mut self.state);
	self.state.v0 ^= mi;
	i += 8;
    }
    self.tail = unsafe { u8to64_le(msg, i, left) };
    self.ntail = left;
}
```
I like the optimism of that `#[inline]` attribute!

Finally, we have the code for finalisation. It's straight-line code this time,
with a number of operations, and calls to two other bit-shuffling functions.
```rust
#[inline]
fn finish(&self) -> u64 {
    let mut state = self.state;
    let b: u64 = ((self.length as u64 & 0xff) << 56) | self.tail;
    state.v3 ^= b;
    S::c_rounds(&mut state);
    state.v0 ^= b;
    state.v2 ^= 0xff;
    S::d_rounds(&mut state);
    state.v0 ^ state.v1 ^ state.v2 ^ state.v3
}
```

# Other hash functions

While every hash function is different, `SipHasher13` is pretty representative
of many of them, with state containing multiple variables and lots of
bit-shuffling for the actual hashing.

The [`fasthash`](https://docs.rs/fasthash/latest/fasthash/) crate aggregates a
number of popular hash functions that are available in Rust. Getting a sense of
the speeds of different hash functions is difficult. In my experience, it is an
exaggeration to say that every hash function implementation claims to be faster
than all the others... but not that much of an exaggeration.

# FxHasher

`FxHasher` is based on a hash function used [within
Firefox](https://searchfox.org/mozilla-central/rev/633345116df55e2d37be9be6555aa739656c5a7d/mfbt/HashFunctions.h#109-153). (Indeed, the `Fx` is short for "Firefox".)

Consider [its
core](https://github.com/rust-lang/rustc-hash/blob/5e09ea0a1c7ab7e4f9e27771f5a0e5a36c58d1bb/src/lib.rs).
The following snippet shows initialisation, the main hash operation, and
finalisation.

```rust
#[inline]
fn default() -> FxHasher {
    FxHasher { hash: 0 }
}

const K: usize = 0x517cc1b727220a95;

#[inline]
fn add_to_hash(&mut self, i: usize) {
    self.hash = self.hash.rotate_left(5).bitxor(i).wrapping_mul(K);
}

#[inline]
fn finish(&self) -> u64 {
    self.hash as u64
}
```

It is brutally simple. Initialisation sets a single variable to zero. Hashing a
value is just a rotate, an xor, and a multiply. Finalisation is a no-op.

(Are you wondering where the constant 0x517cc1b727220a95 comes from?
0xffff_ffff_ffff_ffff / 0x517c_c1b7_2722_0a95 = π.)

In terms of hashing quality, it is mediocre. If you run it through a hash
quality tester it will fail a number of the tests. For example, if you hash any
sequence of N zeroes, you get zero. And yet, for use in hash tables within the
Rust compiler, it's hard to beat. (Fortunately, the compiler is not an
interesting target for [HashDoS
attacks](https://en.wikipedia.org/wiki/Collision_attack).)

Why is this? A lot of hash function are designed to process large amounts of
data. But the most common case in the Rust compiler is hashing a struct with
one or two integer or pointer fields. `FxHasher` is incredibly fast for these
small inputs, partly because its functions are so small that they can be
reliably inlined. (Bigger functions are less likely to be inlined, even if
marked with `#[inline]`. Also, a number of Rust hashing libraries are wrappers
around C libraries, where inlining is not possible. Inlining of intrinsics is
also problematic.)

`FxHasher` can finish hashing a struct with two fields before `SipHasher13` is
done initializing. The quality is good enough that it only results in slightly
more collisions in hash tables than higher quality hash functions, and the raw
hashing speed more than makes up for this.

Also, `FxHasher` is deliberately simplistic in how it handles fields.
`SipHasher13` works in 64-bit chunks. If it is given a `u32` followed by four
`u8`s, it will combine them and process them much like a single `u64`. In
contrast, `FxHasher` will just cast each integer to `usize` and run
`add_to_hash()` five times. (And on 32-bit platforms `u64` inputs are split in
two). Rust's hashing structure permits this behaviour, and it's a good choice
when each `add_to_hash()` is just a rotate, an xor, and a multiply. That is
faster and simpler than trying to accumulate regular sized chunks of data
before hashing. (Note: this is why `SipHasher13` above has a `write()` method
that takes a byte slice but `FxHasher` has an `add_to_hash()` method that takes
a `usize`. See the full implementations for details.)

# Making it faster

Recently I've been trying to improve upon `FxHasher`, and I haven't had much
success. I'm not benchmarking `FxHasher` directly, the metric I use is "does
this make the compiler faster?"

Here are some things I've tried.
- Higher quality algorithms, like `SipHasher13`: range from slightly slower to
  much slower.
- Initialise with one, instead of zero: negligible differences.
- Different multiplication constants: sometimes negligible differences,
  sometimes terrible results.
- Remove the multiply: disastrously slow, due to many more collisions.
- Move the multiply from `add_to_hash` to `finish`: very bad, due to more
  collisions.
- Remove the `rotate_left`: tiny improvements on quite a few benchmarks, but
  moderate regressions on a smaller number, and not worthwhile.
- Change the order from rotate/xor/multiply to xor/multiple/rotate: slightly
slower.

~~The only thing that was a clear win was to change the `#[inline]` attributes to
`#[inline(always)]`, which slightly sped up a couple of benchmarks. Although
the methods are usually inlined, there must have been one or two
performance-sensitive places where they weren't.~~ **Update (Dec 8, 2021):** this turned out
to be a measurement error, and `#[inline(always)]` makes no difference.

After all this, my appreciation for `FxHasher` has grown. It's like a machete:
simple to the point of crudeness, yet unbeatable for certain use cases.
Impressive!

# Postscript

There might be people—including some who have forgotten more about hash
functions than I will ever know—who are furious at my simplistic treatment of
this topic. If you know of a change to `FxHasher` or an alternative algorithm
that might be faster or better, I'd love to hear about it via email, or
Twitter, or wherever else. I just want to make the compiler faster. Thanks!

# **Update (Dec 10, 2021)**

There was some good discussion about this post [on
Reddit](https://www.reddit.com/r/rust/comments/rbe3vn/a_brutally_effective_hash_function_in_rust/).
Reddit user CAD1997 [pointed
out](https://www.reddit.com/r/rust/comments/rbe3vn/a_brutally_effective_hash_function_in_rust/hnsgk1x/)
that `FxHasher`'s handling of the high bits of inputs is poor, because the
multiply effectively throws a lot of them away. This means it performs badly
when hashing a 64-bit integer with low entropy in the low bits.

This was demonstrated when llogiq and I [tried
out](https://github.com/rust-lang/rust/pull/91660) a micro-optimization [idea
from
glandium](https://www.reddit.com/r/rust/comments/rbe3vn/a_brutally_effective_hash_function_in_rust/hnorwqh/)
for combining a struct with two 32-bit fields into a single 64-bit value to be
hashed, rather than hashing them separately. The struct in question is this
one:
```
pub struct DefId {
    pub krate: CrateNum,
    pub index: DefIndex,
}
```
`krate` and `index` are both 32-bit integers. `krate` is a low-entropy value,
typically taking on a small number of distinct values. `index` is a
high-entropy value, typically taking on a large number of distinct values.

If they are combined like this, with the high-entropy field in the low bits:
```
((self.krate as u64) << 32) | (self.index as u64)
```
it's a tiny win compared to hashing them separately.

If they are combined like this, with the high-entropy field in the high bits:
```
((self.index as u64) << 32) | (self.krate as u64)
```
it's a huge slowdown due to a massive increase in hash table collisions.

So it's good to be aware of this weakness when using `FxHasher`. But why does
`FxHasher` still do well in the Rust compiler? First, the compiler is (almost?)
always built as a 64-bit binary, so `FxHasher` is working with 64-bit inputs
and hash values. Second, the values hashed are in three groups.
- Most common are integers. These are (almost?) all 32-bit integers or smaller,
  in which the upper bits are all zero.
- Next most common are pointers. These have very low entropy in the upper bits
  because most memory allocations occur in a small number of distinct sections
  of the address space, such as the heap and the stack.
- Least common are strings. These are hashed by `FxHasher` in 64-bit chunks,
  and so the hash quality won't be good, but it seems they are rare enough that
  it doesn't really hurt performance.

Nonetheless, I am considering using an idea from the
[`ahash`](https://crates.io/crates/ahash) crate. For its
[fallback](https://github.com/tkaitchuck/aHash/blob/master/src/fallback_hash.rs)
variants it can use a clever [folded multiply
operation](https://github.com/tkaitchuck/aHash/blob/e77cab8c1e15bfc9f54dfd28bd8820c2a7bb27c4/src/operations.rs#L11-L14)
that mixes bits well without throwing them away, because the overflow bits from
the multiply get XORed back into the result. And it turns out you can do this
surprisingly cheaply on common platforms. `ahash`'s fallback variants do some
additional initialisation and finalisation work that probably wouldn't benefit
the compiler, so I wouldn't use `ahash` directly. But changing
`FxHasher::add_to_hash()` to use the folded multiply will likely give a hash
function that is as fast while avoiding the potential performance cliffs.

I wrote the original post in the hope of learning about improvements, so I
consider this a good outcome!

# **Update (Feb 25, 2022)**

I tried the folded multiply operation a while ago, but it caused a slight
increase in instruction counts. I realized that the rotate/xor/multiply
sequence used by `FxHasher` is even better than I originally thought. When
hashing a single value (the most common case) the rotate is on the initial
value of zero, which is a no-op that the compiler can optimize away. And then
value being hashed is xor'd onto a zero, which just gives the original value.
So this case ends up optimizing down to a single multiply!

In comparison, the folded multiply requires at least a multiply and an xor.
It's possible that the folded multiply gives better protection against
pathological behaviour, but that possible benefit wasn't enough to take it up
within rustc, at least for now.

However, this is still a chance of [a different
improvement](https://github.com/rust-lang/rust/pull/93651).

