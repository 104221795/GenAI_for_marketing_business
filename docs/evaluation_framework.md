# AI Product Studio Evaluation Framework

This framework evaluates AI Product Studio as a marketing technology product for luxury resale items such as handbags, watches, silk scarves, and premium leather shoes.

## Evaluation Goal

Measure whether the system can transform simple product inputs into campaign-ready luxury marketing assets through AI image generation, channel-specific copy generation, quality scoring, and human-in-the-loop review.

## Recommended Test Campaigns

| Campaign | Product Type | Main Platform | Objective | Funnel Stage |
| --- | --- | --- | --- | --- |
| Quiet Luxury Handbag Drop | Pre-owned leather handbag | Instagram | Conversion | Consideration |
| Collector Watch Feature | Pre-owned luxury watch | Facebook | Conversion | Consideration |
| Silk Scarf Editorial Story | Vintage silk scarf | TikTok | Engagement | Awareness |
| Premium Leather Loafer Listing | Pre-owned leather loafers | Shopee | Conversion | Conversion |

## Evaluation Rubric

| Criterion | Weight | Excellent Standard |
| --- | ---: | --- |
| Product identity preservation | 20% | Logo, material, shape, color, and visible condition remain faithful to the input. |
| Luxury visual quality | 20% | Lighting, surface, styling, shadows, and composition feel premium and realistic. |
| Marketing message fit | 15% | Copy matches audience, platform, funnel stage, brand voice, and campaign objective. |
| Commercial readiness | 15% | Asset can be used for a real listing or social post with minimal editing. |
| Human review usefulness | 10% | Reviewer can compare variants, edit content, choose best output, and approve clearly. |
| Trust and compliance | 10% | Claims are transparent, condition is not exaggerated, and no false partnership is implied. |
| System reliability | 10% | Provider fallback, error handling, storage, export, and audit trail work predictably. |

Score each criterion from 1 to 5:

| Score | Meaning |
| ---: | --- |
| 1 | Poor, not usable |
| 2 | Weak, major revision needed |
| 3 | Acceptable prototype quality |
| 4 | Strong, minor revision needed |
| 5 | Production-ready quality |

Weighted score formula:

```text
Final score = sum((criterion_score / 5) * criterion_weight)
```

Identity approval gate:

- The automated technical screen does not prove product preservation.
- Any AI-edited product without `source_product_overlay` must be compared against the original image before it can be approved; the review action enforces this confirmation.
- Any changed logo, label, color, material surface, or visible condition is a failed product-identity check, regardless of the weighted score.
- A transparent PNG result marked `source_product_overlay` retains the original product layer, but still requires normal publishing review.

## Image Generation Model Benchmark

The system evaluation rubric above measures the workflow as a product. Image-generation provider quality should be measured separately because a technically successful run can still damage the photographed product.

The Evaluation workspace stores one structured assessment per reviewed output using this fidelity-heavy rubric:

| Image Model Criterion | Weight | Excellent Standard |
| --- | ---: | --- |
| Product fidelity | 40% | Shape, logo or label, color, material, hardware, and visible condition match the original image. |
| Scene quality | 20% | Background and product placement look professionally art-directed. |
| Photorealism | 15% | Edges, scale, contact shadow, and lighting appear physically convincing. |
| Scene adherence | 10% | The output follows the selected scenario without unwanted additions. |
| Publish readiness | 15% | No corrective regeneration is needed before publication. |

Identity failures are recorded as structured tags:

| Failure Mode | Interpretation |
| --- | --- |
| Introduced damage or wear | The model added cracks, scratches, stains, creases, or other false condition details. |
| Changed logo or text | Branding, labels, or legible printed details no longer match. |
| Changed color or material | Product appearance is commercially misleading. |
| Altered shape or hardware | Silhouette, clasp, strap, buttons, or construction changed. |
| Product obscured or cropped | The selected scene interferes with product inspection. |
| Unrealistic scene or shadow | Integration quality is poor even when identity is retained. |
| Scene does not match request | The scenario prompt was not followed adequately. |

Model decision policy:

1. The evaluator must view the original product and generated output side by side before submitting a valid model assessment.
2. Any product-identity failure makes the result `failed_product_identity`, even when its numerical score is high.
3. A `publishable_candidate` requires no recorded failure, a product-fidelity rating of at least 4/5, a publish-readiness rating of at least 4/5, and a weighted score of at least 80/100.
4. Report results per model/provider, not only across all outputs, so a cheap fallback model cannot be hidden inside system averages.

Automated technical screening complements but does not replace this benchmark. It measures output dimensions, exposure balance, clipping, detail signal, contrast readability, and optional reference-palette similarity. These measurements cannot isolate the product silhouette or detect a newly invented crack reliably.

## Suggested User Study

Use 5 to 10 reviewers. Suitable reviewer profiles:

- Marketing students
- Small fashion sellers
- Social media content creators
- Online shoppers familiar with luxury resale

For each product:

1. Show the original product photo.
2. Show 3 generated campaign variants.
3. Ask reviewers to select the best variant.
4. Ask reviewers to score the final asset using the rubric.
5. Ask whether they would publish the asset after minor edits.

## Metrics To Report

| Metric | Meaning |
| --- | --- |
| Average weighted score | Overall product quality and readiness |
| Approval rate | Percentage of generated assets approved by reviewers |
| Revision rate | Percentage of assets needing edits |
| Best-variant agreement | Whether reviewers agree with the system-selected best variant |
| Copy usefulness score | Whether generated copy fits platform and buyer intent |
| Trust score | Whether reviewers believe the asset is transparent and credible |
| Identity pass rate by image provider | Percentage of provider outputs without a recorded product-identity failure |
| Publishable rate by image provider | Percentage of provider outputs meeting the strict publishable-candidate rule |
| Mean product fidelity by image provider | Whether a model preserves products consistently across categories and scenes |
| Failure-mode frequency by image provider | Which defects, such as new cracks or changed logos, make a model unsuitable |

## Example Evaluation Summary

```text
Across four luxury resale product categories, AI Product Studio achieved an average weighted score of 82/100. Reviewers rated visual quality and commercial readiness highly, while condition transparency and brand compliance required the most human review. The system was strongest for Instagram handbag campaigns and Shopee loafer listings because the generated outputs matched clear conversion-oriented product goals.
```

## Thesis Interpretation

The system should be described as an AI-assisted marketing workflow, not a fully autonomous marketing engine. Its value comes from combining automation with human judgment:

- AI accelerates image and copy production.
- Heuristic scoring helps prioritize variants.
- Human reviewers preserve brand trust, product accuracy, and commercial judgment.
- Export packages make the output usable for real campaign operations.
