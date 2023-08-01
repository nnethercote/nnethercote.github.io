---
layout: post
title: "How to speed up the Rust compiler: data analysis update"
---

Last week I [requested help with some data analysis of the Rust
compiler](https://nnethercote.github.io/2023/07/25/how-to-speed-up-the-rust-compiler-data-analysis-assistance-requested.html).

The goal here is to improve the size estimate function that guides code
chunking in the Rust compiler's parallel backend. Better estimates should
result in a faster compiler. Basic statistical methods (such as linear
regression) are likely to suffice; advanced machine learning techniques like
supervised learning shouldn't be needed here.

There were some truly excellent responses, many [via
/r/rust](https://www.reddit.com/r/rust/comments/158tcel/how_to_speed_up_the_rust_compiler_data_analysis/),
and multiple requests for more data.

## The responses

[/u/Kulinda](https://www.reddit.com/user/Kulinda) responded [on /r/rust](https://www.reddit.com/r/rust/comments/158tcel/how_to_speed_up_the_rust_compiler_data_analysis/jtd6ixv/).
- They identified two columns (`place` and `proj_`) that were identical.
- They found the best four predictors for the Debug-Primary data set were
  `ty___`, `lc_dc`, `place` `proj_`, and `rval_`.
- There were worried about overfitting due to the smallness of the data sets
  and the lack of test/training data split.
- They suggested `62 * bb___ + 24 * args_` as a 2-value predictor for debug
  builds. I tried this briefly but it gave slightly worse performance in
  practice.
- They found that `inlnd` was important for opt builds.

[/u/jinnyjuice](https://www.reddit.com/user/jinnyjuice) responded [on
/r/rust](https://www.reddit.com/r/rust/comments/158tcel/how_to_speed_up_the_rust_compiler_data_analysis/jte2s65/), and posted longer findings
(including R code) [on their own
site](https://pathosethoslogos.gitlab.io/nnethercote_rust_compiler_model/).
- They said of their technique: "The recipe formulation is pretty simple. It's
  also a meta learner, though only between XGBoost and GLMNET. It doesn't
  really matter for other algorithms (including neural net) -- it was pretty
  much GLMNET."
- They did "a very simple cross validation" to minimize overfitting.
- They found the most important variables were `ty_cn`, `sttic`, `inlnd`,
  and `a_msg`.

[/u/mtijink](https://www.reddit.com/user/mtijink) responded [on /r/rust](
https://www.reddit.com/r/rust/comments/158tcel/how_to_speed_up_the_rust_compiler_data_analysis/jtifa9y/),
and posted a beautiful analysis with plots, R code, and analysis [on their
own site](https://tij.ink/analysis.html).
- They identified that because the data is at a per-CGU level, rather than a
  per-function level, it's impossible to identify any non-linear function-level
  effects.
- They made some good points about repeatability and reproducibility, and how
  the first data sets were very limited on that front.
- They plotted all of the individual features against time, which I found really
  helpful to get a feel for the data.
- They analyzed the limits of accuracy possible with these data sets.
- They suggested `7 * bb___ + 4 * proje` as a 2-value predictor for both debug
  and opt builds. I tried this briefly and it appears to give small
  improvements in compile performance!
- They identified that the data's multicollinearity means that a simple model
  (with few parameters) is likely to do well, and (interestingly) that "for a
  simple model you do not need a large dataset".

[/u/bje2047](https://www.reddit.com/user/bje2047) responded 
[on /r/rust](https://www.reddit.com/r/rust/comments/158tcel/how_to_speed_up_the_rust_compiler_data_analysis/jtdes48/).
- They also noted that non-linearity was a possibility.
- They also noted the lack of a training/test data split.

[/u/jmviz1](https://www.reddit.com/user/jmviz1) responded [on /r/rust](https://www.reddit.com/r/rust/comments/158tcel/how_to_speed_up_the_rust_compiler_data_analysis/jtfdqmy/).
- They suggested the data sets were too small to give reliable results, given
  the number of features and dependent variables.

[/u/Anaxamander57](https://www.reddit.com/user/Anaxamander57) responded
[on /r/rust](https://www.reddit.com/r/rust/comments/158tcel/how_to_speed_up_the_rust_compiler_data_analysis/jtgsxwy/).
- They used a random forest approach to analyze the data.
- For debug builds they identified the five most important features as
  `bb___`, `ty___`, `term_`, `stmt_`, and `vdi__`.
- For opt builds they identified the six most important features as `const`,
  `regn_`, `proje`, `inlnd`, `ty___`, and `lc_dc`.

[/u/rasten41](https://www.reddit.com/user/rasten41) responded [on /r/rust](https://www.reddit.com/r/rust/comments/158tcel/how_to_speed_up_the_rust_compiler_data_analysis/jthv9lj/).
- They also used a random forest approach.
- For opt builds they identified the most important features as `local`,
  `place`, `lc_dc`, `proj_`, `rval_`, `stmt_`, `ty___`.

Jon responded [on
Zulip](https://rust-lang.zulipchat.com/#narrow/stream/247081-t-compiler.2Fperformance/topic/CGU.20size.20estimation.20function/near/378517834).
- They produced tables analyzing the high levels of collinearity.
- They tried various test/training splits and did cross validation.
- Using one technique, they identified the most important features as `sttic`,
  `ty_cn`, `root_`, `const`, `ssd__`, `bb___`, and `inlnd`. Using another
  technique, they got `a_msg`, `const`, `inlnd`, and `ty_cn`.
- They analyzed mtijink's model two-parameter function and found it performed
  quite well.

Felipe responded via email. They did some brief analysis, suggested using
decision trees, and that larger data sets would be helpful.

Matthias responded via email. They suggested a larger data set would be
helpful, as would a training/test split.

## Response summary

That was quite the variety of responses! First of all, a huge thank you to
everyone who put time into helping me with this problem.

If I had to sum up what I've learned, I would say this: if you ask five data
scientists to analyze a data set, you'll get five different answers and four
requests for more data. 😁

There was very little consistency about which were the important features. To
be fair, that is likely due to the limitations of the data sets, which were
small, have multicollinearity, and have no training/test split.

## The new data sets

The demand for more data is clear. I have collected fresh data for 1000 of the
most popular crates on [crates.io](https://crates.io/). Some popular crates
don't compile when run in the test harness, mostly because the harness has some
limitations. I had to try 1131 crates in order to get 1000 that compiled
successfully. Therefore, strictly speaking, this data is for 1000 of the most
popular 1131 crates.

The original data sets had data for just over 40 crates, and only half of those
were "real-world" code. So these new data sets are much bigger.

The data in the files is ordered from the most popular crates to the least
popular.

I have not provided a test/training split, but the data sets are large enough
that people doing analysis can create their own.

I have also significantly changed the columns in the data sets, based on my
"domain expertise"—a combination of digesting the responses, looking at the
compiler's code, and going with my gut feeling.
- I removed a lot of the features that I thought were unlikely to have a
  meaningful effect on the result, and/or which correlated highly with another
  feature. This included some of the features that people had identified as
  important.
- I also believe the old data sets underemphasized the importance of inlined
  functions, which LLVM has to treat very differently to non-inlined functions.
  The old data sets contained count of inlined functions, but had no data about
  their internals. Therefore, I have split all of the relevant intra-function
  features (basic blocks, statements, etc.), separating the counts for inlined
  functions with those for non-inlined functions. Note that inlined functions
  are much more common in opt builds. If I am wrong and inlining is not that
  important, it should be easy to sum the inlined and non-inlined columns for
  each feature.

I haven't provided function-level data that would allow for detection of
non-linearity. It's possible that LLVM's behaviour can be non-linear, but to
detect this would require a lot more data. Sometimes one must draw the line
somewhere, and I have decided to draw it here.

To address the repeatability shortcomings, I generated three versions of each
data set, each one from a different run. The inputs values should be the same
across the data sets, but the timings will vary. They are all still from the
same machine and the same version of the compiler, so I haven't addressed the
reproducibility concerns.

Here are the new data sets:
- [Debug build, top 1000, run 1](/aux/2023/08/01/Debug-Top1000-1.txt)
- [Debug build, top 1000, run 2](/aux/2023/08/01/Debug-Top1000-2.txt)
- [Debug build, top 1000, run 3](/aux/2023/08/01/Debug-Top1000-3.txt)
- [Opt build, top 1000, run 1](/aux/2023/08/01/Opt-Top1000-1.txt)
- [Opt build, top 1000, run 2](/aux/2023/08/01/Opt-Top1000-2.txt)
- [Opt build, top 1000, run 3](/aux/2023/08/01/Opt-Top1000-3.txt)

I have again annotated each file with an explanation of what the columns mean.
I have tried to explain sources of collinearity more clearly this time.

I hope the new data sets will lead to better results! Happy analyzing, and
thank you in advance. Please direct responses to Reddit,
[Zulip](https://rust-lang.zulipchat.com/#narrow/stream/247081-t-compiler.2Fperformance/topic/CGU.20size.20estimation.20function), or email.

