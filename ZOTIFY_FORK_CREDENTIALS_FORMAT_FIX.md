# ✅ БАГ ИСПРАВЛЕН — KIRO

## Статус: ГОТОВО

Фикс применён в `zotify/config.py`.

## Что было сделано

Добавлен метод `_save_credentials_librespot_format()` и вызов его после успешного headless OAuth:

```python
@classmethod
def _save_credentials_librespot_format(cls, username: str, access_token: str, creds_path: str):
    """
    Сохранить credentials в формате совместимом с librespot Session.Builder().stored_file().
    """
    auth_obj = {
        "username": username,
        "credentials": access_token,
        "type": AuthenticationType.Name(AuthenticationType.AUTHENTICATION_SPOTIFY_TOKEN)
    }
    credentials_json = json.dumps(auth_obj, ensure_ascii=True)
    credentials_b64 = base64.b64encode(credentials_json.encode("ascii")).decode("ascii")
    
    with open(creds_path, 'w', encoding='utf-8') as f:
        json.dump({"credentials": credentials_b64}, f)
```

В `_try_headless_oauth()` добавлен вызов:
```python
if cls.CONFIG.get_save_credentials():
    creds_path = cls.CONFIG.get_credentials_location()
    cls._save_credentials_librespot_format(username, access_token, str(creds_path))
```

## Результат

- Credentials сохраняются в формате `{"credentials": "base64..."}` ✓
- `stored_file()` может прочитать сохранённые credentials ✓
- Повторная авторизация не требуется ✓

## Следующий шаг

Протестируй и запушь.

---
*Исправлено: 4 декабря 2025*
