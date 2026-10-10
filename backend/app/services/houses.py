def whole_sign_house(planet_sign_index: int, ascendant_sign_index: int) -> int:
    return ((planet_sign_index - ascendant_sign_index) % 12) + 1

def whole_sign_houses(ascendant_sign_index: int):
    return {
        str(h): {
            "sign_index": ((ascendant_sign_index - 1 + h - 1) % 12) + 1
        }
        for h in range(1, 13)
    }
