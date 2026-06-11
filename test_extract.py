"""
test_extract.py — valida o parser da Decolar contra um HTML salvo, SEM rede.
Uso: python test_extract.py sample_Decolar2.txt
"""
import sys

from scraper import parse_rooms, derive_categories, classify


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "sample_Decolar2.txt"
    html = open(path, encoding="utf-8", errors="replace").read()

    rooms = parse_rooms(html)
    print(f"Quartos encontrados: {len(rooms)}\n")
    for name, price in sorted(rooms.items(), key=lambda kv: kv[1]):
        c = classify(name)
        tags = " ".join(t for t, v in (("[mar]", c["ocean"]), ("[suíte]", c["suite"])) if v)
        print(f"  R$ {price:>9,.0f}  {name}  {tags}")

    cats = derive_categories(rooms)
    print("\nCategorias derivadas:")
    for k, pick in cats.items():
        if pick:
            print(f"  {k:18} R$ {pick['price']:>9,.0f}  ({pick['room_name']})")
        else:
            print(f"  {k:18} —")


if __name__ == "__main__":
    main()
