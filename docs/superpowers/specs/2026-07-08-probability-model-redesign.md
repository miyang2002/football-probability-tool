# Football Probability Model Redesign

## Objective

Redesign the football analysis tool so every recommendation is explainable in plain Chinese and backed by two separate reference lines:

- 官方赔率模型: uses official China Sports Lottery odds.
- 球队资料模型: uses recent form, injuries, schedule motivation, and news when available.

The first implementation should build the full architecture and user-facing result structure, while allowing external team/news data sources to be added or improved incrementally. If team data is missing, the app still works and clearly says which information is missing.

## Scope

This redesign covers all five football markets:

- 胜平负
- 让球胜平负
- 比分
- 总进球
- 半全场

Each market must show:

- 官方赔率模型建议
- 球队资料模型建议
- 综合建议
- 缺失信息

The main display must use plain-language betting-style explanations:

- Which model recommends what.
- What the official odds are.
- How much a 2 yuan stake returns if hit.
- Why the combined recommendation is reasonable.

Avoid main-page terms such as EV, expected value, theoretical loss, model edge, or "odds too low".

## Architecture

The redesign has three layers.

### Official Odds Model

Use the official China Sports Lottery odds already fetched from the Sporttery calculator endpoint:

- `had`: 胜平负
- `hhad`: 让球胜平负
- `crs`: 比分
- `ttg`: 总进球
- `hafu`: 半全场

For each market, convert odds to normalized market probabilities within that same market. Do not mix unrelated market probabilities through crude weighted addition.

For correct score, include every official Sporttery score option:

- Concrete scorelines, such as `1-0`, `2-1`, `0-0`
- `胜其它`
- `平其它`
- `负其它`

The official score market must use Sporttery data as-is. Do not split `胜其它`, `平其它`, or `负其它` into fake scorelines.

### Team Information Model

Automatically collect team information where possible:

- Recent form: last 5 to 10 matches.
- Goals scored and conceded.
- Home/away split when relevant.
- Injuries and suspensions.
- Schedule and motivation.
- News, including Chinese sources first and translated English summaries when useful.

Every collected item must carry:

- Source name
- Source URL when available
- Updated time
- Confidence level
- Whether it affected the model or was only shown as a reminder

Evidence rules:

- Official confirmation can affect the model.
- Multiple credible sources saying the same thing can affect the model.
- A single low-confidence item is shown as a reminder and should not strongly affect the model.
- Conflicting items are shown as conflicts and reduce that information category's weight.

If team information cannot be fetched, the model must show it as missing. It must not invent form, injuries, or tactical facts.

### Combined Recommendation Layer

Combine the official odds model and the team information model using dynamic weights:

- If team information is complete and recent, it gets more weight.
- If team information is missing, old, or conflicting, it gets less weight.
- The page must show the current model weights, such as `赔率模型 75% / 球队资料模型 25%`.

The combined advice levels remain exactly:

- 建议
- 小额参考
- 谨慎
- 放弃

For the score market, the lowest level should be displayed in a softer entertainment-oriented way, such as `仅作娱乐参考`, instead of "放弃比分玩法".

## Correct Score Model

Correct score is the most important redesign area because the current model can produce identical recommendations across different matches.

### Official Score Probability

For each match:

1. Read all official Sporttery score options.
2. Convert every score option's odds into implied probability.
3. Normalize across all official score options, including `胜其它`, `平其它`, and `负其它`.
4. Display the official odds and 2 yuan return exactly from the Sporttery quote.

This produces the official score model.

### Team Information Score Probability

When team data is available:

1. Estimate attacking and defensive strength from recent matches, goals scored, goals conceded, home/away context, injuries, schedule, and motivation.
2. Estimate full-match scoring tendency.
3. Generate a score distribution with a Poisson or similar goal-distribution model.
4. Map the model score distribution to Sporttery settlement options:
   - If a scoreline exists in official Sporttery quotes, keep that concrete scoreline.
   - If a model scoreline does not exist in Sporttery quotes, map it to `胜其它`, `平其它`, or `负其它`.
5. Keep all probabilities in the same market option space as the official score model.

If team data is missing, show `球队资料概率缺失`, and use the official odds model as the main basis for the combined score probability.

### Consistency Checks

The other four markets may support or conflict with score candidates, but they must not be blindly added into score probability.

For each score candidate, check:

- Whether it matches the win/draw/loss direction.
- Whether it matches handicap direction.
- Whether its total goals match total-goals odds.
- Whether it is compatible with half-time/full-time market signals.
- Whether team information supports or conflicts with it.

Consistency can adjust the combined probability and advice level, but the adjustment must be capped so independent markets are not double-counted.

### Score Candidate Table

The score row expands into a candidate table.

Default view:

- Show the top 5 candidates.
- Sort by combined advice level first, then combined probability.

Expanded view:

- Show additional candidates.
- Show `胜其它`, `平其它`, and `负其它` as official options when relevant.
- If model scorelines are grouped into an "other" option, show the grouped option first and allow details to list the concrete model scorelines inside it.

Each row must show:

- 比分 or official option
- 官方赔率模型概率
- 球队资料模型概率
- 综合概率
- 官方比分赔率
- 2元一注中出返还
- Ranking and confidence
- Support items
- Conflict items
- Plain-language reason

If a concrete model scoreline has no official Sporttery quote, display both:

- 模型比分: `4-1`
- 体彩选项: `胜其它`

The payout uses the `胜其它` quote.

## Five-Market Result Table

Each match detail page should present a concise Chinese result table with five rows:

- 胜平负
- 让球胜平负
- 比分
- 总进球
- 半全场

Each row should use the same structure.

### Official Odds Model Column

Show:

- 市场最看好
- 回报参考
- Official odds
- 2元一注中出返还
- Market probability after normalization

Example:

`体彩更看好 2-0，赔率 6.25，2元中出返还 12.50元。`

### Team Information Model Column

Show:

- Model recommendation
- Probability
- Confidence
- Main plain-language basis
- Missing information if unavailable

Example:

`球队资料更偏向 1-0，概率 12.4%，依据是主队近期进攻更稳定，客队进球能力偏弱。`

If team data is unavailable:

`球队资料缺失，本场资料模型暂不参与，综合建议主要依据体彩赔率。`

### Combined Advice Column

Show a plain recommendation:

- What to mainly reference.
- Which alternative is for higher return.
- What risk or conflict exists.
- How a 2 yuan stake pays if the chosen option hits.

Example:

`综合方案：优先参考 1-0 / 2-0；两边方向接近，比分仍属于低概率玩法，仅作娱乐参考。`

## Data Refresh

Refresh in layers:

- Official odds: every 30 to 60 seconds.
- Team data and news: every 30 minutes.
- Team data and news within 2 hours before kickoff: every 10 minutes.

The page should load in stages:

1. Show official odds analysis first.
2. Fetch team information in the background.
3. Update team model and combined advice when team data arrives.
4. Show updated times for odds and team information separately.

## Missing Data Behavior

Missing data must be visible and specific.

Examples:

- `官方比分赔率缺失`
- `球队近况未抓到`
- `伤停信息缺失`
- `新闻来源冲突`
- `半全场赔率缺失`

If team data is missing, still show full recommendations based on official odds and clearly label that the combined probability is mainly odds-driven.

If official odds for a market are missing, do not create fake official odds. The row should still show the team-information model if available and mark official odds as missing.

## Plain-Language Copy Rules

Use simple Chinese throughout the main UI.

Use:

- `模型看好`
- `体彩更看好`
- `回报参考`
- `2元一注中出返还`
- `两边一致`
- `两边分歧`
- `资料不足，参考性下降`
- `仅作娱乐参考`

Avoid:

- `EV`
- `期望值`
- `理论盈亏`
- `每100元少多少钱`
- `模型比赔率高多少`
- `赔率偏低`
- `价值投注`

Probabilities should be shown, but every important probability should be paired with plain explanation, ranking, or confidence so the user does not mistake a low-probability scoreline for a sure result.

## Reliability Boundaries

The tool is for entertainment and rational probability analysis. It does not guarantee results.

The score market must explicitly account for the fact that exact score probabilities are usually low. Even the highest-probability scoreline is often only in the single digits to low teens.

The goal is not to claim certainty. The goal is to:

- Use real official odds.
- Use real team information where available.
- Show missing data honestly.
- Make different matches produce meaningfully different recommendations.
- Explain the recommendation in plain Chinese.

## Testing Requirements

Add or update tests for:

- Official score odds include concrete scores plus `胜其它`, `平其它`, and `负其它`.
- Score model maps unavailable concrete scorelines to the correct "other" option.
- Normalized official market probabilities include all official score options.
- Missing team data does not block odds-based recommendations.
- Five markets all return official model, team model, combined advice, and missing information.
- Main UI copy avoids technical terms rejected by the user.
- Score candidate table includes probability, odds, and 2 yuan return.
- Different odds/team inputs produce different score recommendations.

## Implementation Strategy

Use the selected implementation strategy: full architecture with staged rollout.

First implementation should build:

- Shared result schema for official model, team model, and combined advice.
- Correct score candidate table and "other" mapping.
- Official odds model for all five markets.
- Team data provider interface and empty/missing-data behavior.
- Basic free data/news provider hooks where feasible.
- Layered refresh status.
- Plain-language UI.

After this foundation is working, improve team data coverage incrementally without changing the main user-facing model contract.
