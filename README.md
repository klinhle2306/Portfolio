# Linh Le · Portfolio

Personal portfolio site, live at **[klinhle2306.github.io/Portfolio](https://klinhle2306.github.io/Portfolio/)**.

## Projects

| Project | What it is | Folder |
|---|---|---|
| Texas ER Wait Times | What predicts a long ER visit, using CMS data on 401 Texas hospitals | [`projects/texas-er-wait-times`](projects/texas-er-wait-times) |
| Production Traceability | Replacing handwritten crate labels with a rules-based Python generator | [`projects/chenmega-traceability`](projects/chenmega-traceability) |
| Fragrance-Free Report | Does a "clean beauty" claim predict better ratings? 1,472 Sephora products | [`projects/fragrance-report`](projects/fragrance-report) |
| Asthma Risk Research | Oversampling methods for imbalanced healthcare data, published at IEEE ICCDA 2023 | [`projects/asthma-research`](projects/asthma-research) |
| Movie Recommender | Collaborative filtering with Apache Spark MLlib on MovieLens | [`projects/movie-recommender`](projects/movie-recommender) |
| SQL Portfolio | Five SQL analysis projects | [separate repo](https://github.com/klinhle2306/SQL-Portfolio) |

## Layout

```
index.html, about.html     site pages
assets/                    shared images, pixel-art sprites, resume
projects/<name>/
    index.html             the project's write-up page
    code/                  analysis scripts and notebooks
    data/                  datasets the code reads
    graphs/                charts shown on the page
    pictures/              photos
    icons/                 inventory icon for the homepage
    docs/                  posters and other documents
```

Each project's scripts use paths relative to their own folder, so they can be run from anywhere, e.g. `python projects/texas-er-wait-times/code/er_analysis.py`.
