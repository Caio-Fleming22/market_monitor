def parse_name(full_name):
    import pandas as pd
    from datetime import datetime
    
    # Caso o nome contenha um hífen
    if '-' in full_name:
        name, date_code = full_name.split('-')
        year = int('20' + date_code[:2])
        month = int(date_code[2:])
        expiry_date = f"{year}-{month:02d}-30"  # Assume dia 30
        net = 'Solana'
        label = f"{name} (Expires in: {expiry_date}) {net}"
    else:
        # Caso o nome não contenha um hífen, tratamos de outra maneira
        name = full_name
        expiry_date = "2026-12-30"  # Exemplo de data de expiração padrão
        net = "Unknown"
        label = full_name

    address = -1  # Para fins de exemplo, assume-se -1 como endereço (isso pode ser alterado)
    return {
        'name': name,
        'address': address,
        'expiry_date': expiry_date,
        'net': net,
        'label': label
    }
