"""
Economy Reset Script for Phantom Regiment
- Awards 'Phantom Regiment Elite' role purchase to users with 10k+ medals
- Wipes ALL medals, bank balances, loans, streaks
- Run ONCE before deploying the global sync update
"""
import sqlite3
import time

DB_PATH = "bot.db"
PR_GUILD_ID = 1550544659217125467

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Step 1: Find users with 10k+ medals (wallet + bank combined)
rich = conn.execute("""
    SELECT u.user_id, u.medals, COALESCE(b.balance, 0) as bank, 
           (u.medals + COALESCE(b.balance, 0)) as total
    FROM users u 
    LEFT JOIN banks b ON u.user_id = b.user_id AND u.guild_id = b.guild_id
    WHERE u.guild_id = ? AND (u.medals + COALESCE(b.balance, 0)) >= 10000
""", (PR_GUILD_ID,)).fetchall()

print(f"Found {len(rich)} users with 10k+ medals:")
for r in rich:
    print(f"  User {r['user_id']}: wallet={r['medals']:,}, bank={r['bank']:,}, total={r['total']:,}")
    # Award Phantom Regiment Elite role
    try:
        conn.execute(
            "INSERT OR IGNORE INTO role_purchases (user_id, guild_id, role_key) VALUES (?, ?, ?)",
            (r['user_id'], PR_GUILD_ID, 'role_phantom')
        )
        print(f"    -> Awarded Phantom Regiment Elite role purchase")
    except Exception as e:
        print(f"    -> Error awarding role: {e}")

# Step 2: Wipe ALL medals
conn.execute("UPDATE users SET medals = 0")
print("\n[WIPED] All wallet medals set to 0")

# Step 3: Delete ALL bank accounts (they'll need to recreate with passwords)
conn.execute("DELETE FROM banks")
print("[WIPED] All bank accounts deleted")

# Step 4: Clear ALL loans
conn.execute("DELETE FROM bank_loans")
conn.execute("DELETE FROM player_loans")
print("[WIPED] All bank and player loans cleared")

# Step 5: Reset streaks
conn.execute("DELETE FROM streaks")
print("[WIPED] All daily streaks reset")

# Step 6: Reset cooldowns
conn.execute("UPDATE users SET last_daily = 0, last_work = 0, last_weekly = 0")
print("[WIPED] All cooldowns reset")

conn.commit()
conn.close()
print("\n✅ Economy reset complete! Ready for global sync deployment.")
