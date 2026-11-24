# A1 English pronoun boundaries

The current-product JVM replay reproduced a manual `I` suggestion for the
last letter of `Baha'i` and `value_i`. Boundary commits kept the literal
text. The controller now refuses that suggestion when the owned left context
ends in an underscore or an apostrophe attached to a letter or digit. Both
straight and typographic apostrophes are covered. An opening quote after
whitespace still permits the manual suggestion.

Two runs of 22 disclosed cases per boundary gave identical behavioral
projections. All 66 cases preserved the typed text on space, period and colon
and had no automatic edit. The manual suggestion was absent for both
apostrophe forms, the two identifier forms, and the Spanish/Russian layouts.
It remained available for isolated English `i` and for an opening quote.
Ambiguous Roman numerals, spaced code and Spanish text typed on the English
layout can still show the manual suggestion. These are local controller
observations.

| Boundary | Behavioral projection SHA-256 |
| --- | --- |
| Space | `63e25fddff1aafb38fab769658a58bffcd091dbea627962184454ade276b611e` |
| Period | `0db26bd17c3de728b3fafbbdf3e8bdc5641fe19b020a4fd402e2c49b65ef4545` |
| Colon | `ff37d30fc666ecb22de32cebb8159fb8a0bbedf8cd4cb04855ea27b0d2125e08` |

The replay bindings cover 91 source files and 63 assets at
`4ef3daafbd7577ba5ae023fd6cc2f3dfb9f163a86dab9e00cef4b8b8bdc60dde`.
The first unprojected comparison also included varying host timing fields.
The projected comparisons check text, candidates and controller edit state.
The targeted offline Gradle run passed all 132 controller-boundary tests
and 36 candidate-generator tests, with zero failures or skips.
The local CI replay command matched both frozen projections across 2,160
multilingual rows and 12,000 historical spelling rows, with zero tolerated
score differences. The temporary compile, Gradle and replay folders were
removed after the checks.

## Annotated source screen

The pinned UD English GUM release `b58e74bc22d17220c9198864c253a50a897bf27f`
was read twice in memory. All three split downloads matched byte for byte.
The scan aligns literal English `I/i` occurrences with the same annotated
sequence and counts a boundary of whitespace or `, ! ? ; :`. It omits
unaligned sentences. The publishers list CC BY-NC-SA 4.0 for this treebank.
[UD English GUM](https://universaldependencies.org/treebanks/en_gum/)
[Pinned source](https://github.com/UniversalDependencies/UD_English-GUM/tree/b58e74bc22d17220c9198864c253a50a897bf27f)

Among aligned lowercase occurrences before those boundaries, training has
two pronouns and ten other POS tags. Six of those ten follow another word
and whitespace. Development and test contain zero lowercase occurrences in
this slice. Expanding the comparison to both cases produces three training
preceding-word values shared by pronouns and other POS tags. These are
annotation and surface-context counts.

| GUM split | SHA-256 |
| --- | --- |
| Train | `88c410ca6a51ccc79f9536d75feb1633421691165cd191f8137f8b37569a0329` |
| Dev | `61d02ce27a143e9749118b1b9c314ac3da40f64ec17a6aaff5fc7b42704f7910` |
| Test | `cd96a285e7339f401f4803dd0f4f61109c51692e3ef6f9186a1f977544080b69` |

Automatic conversion, fresh independent qualification, and physical Fold
coverage remain open. The GUM scan retained aggregate counts and no source
text.
