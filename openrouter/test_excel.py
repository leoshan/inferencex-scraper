import pandas as pd
from datetime import datetime, timezone
df = pd.DataFrame({'a': [datetime.now(timezone.utc)]})
try:
    with pd.ExcelWriter('test.xlsx', engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Sheet1')
except Exception as e:
    print(repr(e))
