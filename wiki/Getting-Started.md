# Getting Started · Hostess 7 4.0.0-cpp

## Install

```bash
git clone https://github.com/ZacharyGeurts/Hostess7.git
cd Hostess7
```

Optional rebuild of field tools:

```bash
make -C native/field-tools field-hostess7 field-ammoos
# or full set
make -C native/field-tools all
```

## Bring online

```bash
./bin/field-hostess7 online
# AmmoOS desktop
./bin/field-ammoos online
```

Open:

- Local OS: http://127.0.0.1:9477/field  
- Pages OS: https://zacharygeurts.github.io/Hostess7/desktop/  

## Verify

```bash
./bin/field-hostess7 status
./bin/field-ammoos status
./bin/field-hostess7 brain
./bin/field-hostess7 package
```

Expect `engine=cpp`, `python=0`, `scripts=0`, `field_one=1`, `online=1`.

## Obsolete paths

Do **not** use for ops:

- `pip install -r requirements.txt` as control  
- `./Hostess7.sh` as shell (name may be ELF alias)  
- JSON “control panels” → use `FIELD_PLATE=v1`  

See [[Cpp-Control-Plane]] · [[AmmoOS-Desktop]]
