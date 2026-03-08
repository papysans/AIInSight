import ast, os

errors = []
for base in ['app', 'opinion_mcp']:
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for f in files:
            if not f.endswith('.py'):
                continue
            path = os.path.join(root, f)
            try:
                with open(path) as fh:
                    ast.parse(fh.read(), filename=path)
            except SyntaxError as e:
                errors.append(f'{path}: line {e.lineno}: {e.msg}')

if errors:
    print('SYNTAX ERRORS:')
    for e in errors:
        print(f'  {e}')
else:
    print('All Python files parse OK')
