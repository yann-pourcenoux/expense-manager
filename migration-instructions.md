# Database Migration Instructions

To support the new features in the expense manager, you need to run the following SQL commands in your Supabase SQL editor:

```sql
-- Add beneficiary_id column to the expenses table
ALTER TABLE expenses ADD COLUMN IF NOT EXISTS beneficiary_id int8 REFERENCES profiles(id);

-- Add amount column to the expenses_split table
ALTER TABLE expenses_split ADD COLUMN IF NOT EXISTS amount numeric DEFAULT 0;
```
