import altair as alt
from vega_datasets import data
import pandas as pd

source = data.movies.url

print(pd.DataFrame(source))