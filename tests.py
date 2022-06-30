import pandas as pd

df = pd.read_json('data/last_updated.json')

df.to_html('test_table.html',index=False)