---
layout: post
title: Quirks of Rust's token representation
---

Like most compilers, `rustc` (the Rust compiler) has a lexer that breaks source
code into tokens, which are small units such as identifiers, literals,
operators, and punctuation. The parser then checks that these tokens are
present in an order that satisfies Rust's grammar.

Rust has many fixed-length tokens, mostly operators and punctuation:
- One-char: `;`, `,`, `.`, `(`, `)`, `{`, `}`, `[`, `]`, `@`, `#`, `~`, `?`,
  `:`, `$`, `=`, `!`, `<`, `>`, `-`, `&`, `|`, `+`, `*`, `/`, `^`, `%`.
- Two-char: `==`, `&&`, `||`, `+=`, `-=`, `*=`, `/=`, `%=`, `^=`, `&=`, `|=`,
  `<<`, `>>`, `..`, `::`, `<-`, `->`, `=>`.
- Three-char: `<<=`, `>>=`, `...`, `..=`.

Every two-char and three-char token starts with a character that is also a
legitimate one-char token. If the lexer sees two `&&` characters in a row, is
it seeing two `&` reference operators, or is it seeing a `&&` logical AND
operator? It can't tell, because it doesn't have enough information. Not until
full parsing is done can this decision be made, based on the syntactic context.

So the compiler designers must make a choice between two representations.
- Split: Represent a multi-char sequence like `&&` as multiple single-char
  tokens, and combine them when necessary.
- Joined: Represent a multi-char sequence like `&&` as a single token, and
  split it when necessary.

`rustc` does... a mixture of the two. It's complicated.

`rustc` actually has two lexers.
- The first lexer is in the [`rustc_lexer`
  crate](https://github.com/rust-lang/rust/tree/f83e0266cf7aaa4b41505c49a5fd9c2363166522/compiler/rustc_lexer/src),
  which is shared between `rustc` and `rust-analyzer`. Its
  [tokens](https://github.com/rust-lang/rust/blob/f83e0266cf7aaa4b41505c49a5fd9c2363166522/compiler/rustc_lexer/src/lib.rs#L54-L147)
  use a split representation.
- The second lexer is in the [`lexer`
  module](https://github.com/rust-lang/rust/tree/master/compiler/rustc_parse/src/lexer)
  of the [`rustc_parse`
  crate](https://github.com/rust-lang/rust/tree/f83e0266cf7aaa4b41505c49a5fd9c2363166522/compiler/rustc_parse/src).
  It converts the first lexer's tokens into [AST
  tokens](https://github.com/rust-lang/rust/blob/f83e0266cf7aaa4b41505c49a5fd9c2363166522/compiler/rustc_ast/src/token.rs#L186-L257),
  which use a joined representation. The parser splits tokens when necessary
  using a method
  [`Parser::break_and_eat`](https://github.com/rust-lang/rust/blob/dbaf3e67aa156db0031a24383f3cc371a10da13b/compiler/rustc_parse/src/parser/mod.rs#L687-L717).

Plus there is a third token representation: proc macros receive and produce a
[`proc_macro::TokenStream`](https://doc.rust-lang.org/proc_macro/struct.TokenStream.html).
These token streams use the split strategy for the
[`Punct`](https://doc.rust-lang.org/proc_macro/struct.Punct.html) type, in
combination with the
[`Spacing`](https://doc.rust-lang.org/proc_macro/enum.Spacing.html) type that
indicates if two adjacent tokens can be joined.

When converting from AST tokens to proc macro tokens, joined tokens are
[resplit](https://github.com/rust-lang/rust/blob/dbaf3e67aa156db0031a24383f3cc371a10da13b/compiler/rustc_expand/src/proc_macro_server.rs#L113-L122).
And when converting from proc macro tokens back to AST tokens, split tokens are
[rejoined](https://github.com/rust-lang/rust/blob/dbaf3e67aa156db0031a24383f3cc371a10da13b/compiler/rustc_ast/src/tokenstream.rs#L556-L574).

I finally got all this clear in my head [just last
week](https://github.com/rust-lang/rust/pull/102508#discussion_r984970100).
I'm now wondering whether the AST tokens could be changed to a split
representation. That way, split representations would be used everywhere. I
haven't yet investigated how difficult this would be, nor what the benefits
might be.

**Update:** Aleksey Kladov pointed out an existing
[issue](https://github.com/rust-lang/rust/issues/63689) suggesting exactly this
change to AST tokens.

