def up(cursor, bot):
    cursor.execute('ALTER TABLE "playsound" ADD COLUMN IF NOT EXISTS tier INTEGER DEFAULT NULL')
