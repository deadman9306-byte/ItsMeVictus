One Command Install And Full Setup /n

git clone https://github.com/deadman9306-byte/ItsMeVictus.git && cd ItsMeVictus && bash setup.sh && sed -i -e 's|SUPABASE_URL   = "https://YOUR_PROJECT.supabase.co"|SUPABASE_URL   = "https://fyzbqbubsdkjrmppkdsl.supabase.co"|' -e 's|SUPABASE_KEY   = "YOUR_SERVICE_ROLE_KEY"|SUPABASE_KEY   = "sb_secret_uef_qoRHTsWrsx727Kh0Ug_bSTJ48uK"|' -e 's|SUPABASE_TABLE = "YOUR_TABLE_NAME"|SUPABASE_TABLE = "layer4_apis"|' config.py && python3 main.py
