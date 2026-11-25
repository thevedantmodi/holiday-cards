# Holiday cards

Makes printable photo postcards for a list of friends. The front has three of
your photos, a script signature and a greeting. The back has a small photo, a
short note, your return address, a stamp box and the friend's address.

![preview](docs/preview.png)

## Quick start

1. Put four photos in the `photos/` folder, named:
   - `main.jpg`: the large photo on the front (a portrait photo works best)
   - `top.jpg` and `bottom.jpg`: the two small photos on the front
   - `back.jpg`: the small photo on the back

   Any size works. Each photo is cropped to fill its spot, and phone photos
   come out the right way up.
2. Edit `config.toml`: your signature, greeting, date, return address and note.
3. Make your friends list:
   ```bash
   cp friends.example.csv friends.csv
   ```
4. Make the cards. They are written to `out/postcards.pdf`:
   ```bash
   python3 postcards.py friends.csv
   ```

If a photo is missing, a labeled gray box shows where it goes. You need Python
3.11+ with `reportlab` and `pillow` (`pip install reportlab pillow`).

## Friends list (`friends.csv`)

| column     | required | notes |
|------------|----------|-------|
| `name`     | yes      | full name. The first word is used as `{first_name}` |
| `address1` | yes      | street address |
| `address2` |          | apartment or unit |
| `city`, `state`, `zip` | yes | |
| `country`  |          | printed only when it isn't the US |
| `message`  |          | replaces the note on the back for this friend |

`friends.csv` and `photos/` are in `.gitignore`, so your friends' addresses and
your photos stay out of git.

## Fixing a crop

If a crop cuts off someone's head, add a focus point in `config.toml` that
says which part of the photo to keep in view. It is given as
`[left-to-right, top-to-bottom]`, from 0 to 1:

```toml
[focus]
main = [0.5, 0.25]   # keep the upper middle of the main photo in view
```

## Printing

- Each page is 6 × 4 in, the standard USPS postcard size. Pages go front, back,
  front, back.
- Print double-sided on 4×6 card stock (about 110 lb / 300 gsm), with
  **flip on short edge** and the scale set to 100%. Print one test card first.
- The bottom 5/8 in of the address side is left blank for the USPS barcode.

## Fonts

The cards use Cormorant Garamond, Herr Von Muellerhoff and Montserrat. All
three are free Google Fonts under the SIL Open Font License, and they are
included in `fonts/` with their license files.
