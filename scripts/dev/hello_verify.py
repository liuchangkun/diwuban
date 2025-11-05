from pathlib import Path
Path('.artifacts').mkdir(parents=True, exist_ok=True)
Path('.artifacts/_hello.txt').write_text('hello', encoding='utf-8')
print('hello_written')

