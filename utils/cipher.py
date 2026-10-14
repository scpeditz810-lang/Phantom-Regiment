"""
Phantom Regiment Cipher System
Multi-layer encryption for robbery hints.
Designed to be genuinely difficult for AI to decrypt.
"""
import hashlib
import random
import time

# Custom symbol alphabets for obfuscation
RUNIC = 'ᚠᚡᚢᚣᚤᚥᚦᚧᚨᚩᚪᚫᚬᚭᚮᚯᚰᚱᚲᚳᚴᚵᚶᚷᚸᚹᚺᚻᚼᚽᚾᚿᛀᛁᛂᛃᛄᛅᛆᛇᛈᛉᛊᛋᛌᛍᛎᛏᛐᛑᛒᛓ'
ALCHEMY = '🜁🜂🜃🜄🜅🜆🜇🜈🜉🜊🜋🜌🜍🜎🜏🜐🜑🜒🜓🜔🜕🜖🜗🜘🜙🜚🜛🜜'
NOISE_POOL = '░▒▓█▀▄▌▐■□▢▣▤▥▦▧▨▩▪▫▬▭▮▯'
DIVIDERS = ['⟐', '⟑', '⟒', '⟓', '⟔', '⟕', '⟖', '⟗']

def _xor_shift(data: list[int], seed: int) -> list[int]:
    """XOR each byte with a pseudo-random stream seeded from the timestamp."""
    state = seed
    result = []
    for b in data:
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        key_byte = (state >> 16) & 0xFF
        result.append(b ^ key_byte)
    return result

def _columnar_transpose(text: str, key: int) -> str:
    """Rearrange characters using columnar transposition."""
    cols = max(3, (key % 5) + 3)  # 3-7 columns
    # Pad
    padded = text + NOISE_POOL[0] * (cols - len(text) % cols) if len(text) % cols != 0 else text
    rows = [padded[i:i+cols] for i in range(0, len(padded), cols)]
    # Read columns in shuffled order
    order = list(range(cols))
    rng = random.Random(key)
    rng.shuffle(order)
    result = ''
    for col_idx in order:
        for row in rows:
            if col_idx < len(row):
                result += row[col_idx]
    return result

def _segment_reverse(text: str, chunk_size: int) -> str:
    """Reverse every other chunk of the string."""
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    return ''.join(chunk[::-1] if i % 2 == 1 else chunk for i, chunk in enumerate(chunks))

def _inject_noise(text: str, seed: int) -> str:
    """Insert noise characters at pseudo-random intervals."""
    rng = random.Random(seed + 42)
    result = ''
    for i, c in enumerate(text):
        result += c
        if rng.random() < 0.35:  # ~35% chance to inject noise
            result += random.choice(NOISE_POOL)
    return result

def _to_runic(data: list[int]) -> str:
    """Convert byte values to runic symbols."""
    result = ''
    for b in data:
        # Map to runic + alchemy symbols
        high = (b >> 4) & 0x0F
        low = b & 0x0F
        result += RUNIC[high % len(RUNIC)] + ALCHEMY[low % len(ALCHEMY)]
    return result

def encrypt_robber_hint(robber_name: str, timestamp: float) -> str:
    """
    Encrypt the robber's name through 5 layers of obfuscation.
    Returns a string that looks like complete gibberish but is technically
    decodable if you reverse all 5 layers in the correct order.
    """
    seed = int(timestamp) % 100000
    
    # Layer 1: Convert name to bytes, XOR with timestamp-derived stream
    raw_bytes = [ord(c) for c in robber_name]
    xored = _xor_shift(raw_bytes, seed)
    
    # Layer 2: Convert XOR'd bytes to runic symbols
    runic_text = _to_runic(xored)
    
    # Layer 3: Columnar transposition
    transposed = _columnar_transpose(runic_text, seed)
    
    # Layer 4: Reverse every other chunk of 4 characters
    reversed_segs = _segment_reverse(transposed, 4)
    
    # Layer 5: Inject noise characters
    noisy = _inject_noise(reversed_segs, seed)
    
    # Add decorative dividers to make it look even more alien
    divider = DIVIDERS[seed % len(DIVIDERS)]
    final_chunks = [noisy[i:i+8] for i in range(0, len(noisy), 8)]
    return f' {divider} '.join(final_chunks)

def hash_password(password: str) -> str:
    """Hash a bank password using SHA-256 with a salt."""
    salt = 'PhantomRegiment_v2_'
    return hashlib.sha256((salt + password).encode()).hexdigest()

def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against its stored hash."""
    return hash_password(password) == stored_hash
