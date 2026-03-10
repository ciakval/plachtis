# Registrace lodí a Plavenky

Tento dokument popisuje funkcionalitu PlachtISu pro registraci lodí na akci a pro plavenky.

## Potřeby z hlediska závodu

* vědět jaké posádky se přihlašují do závodu, včetně údajů o jednotlivých členech posádky a o lodi

## Potřeby z hlediska plavenek

* mít přehled o všech plavidlech, která se na akci vyskytují
* za pomoci fyzických kartiček (plavenek), které lodě musí povinně mít s sebou na vodě, mít v každém okamžiku přehled o tom, které lodě jsou na vodě a které na břehu
  * být schopen připravit podklady pro hledání ztracené lodi či evakuaci vodní hladiny
  * být schopen prokázat, že po dobu akce mělo vedení akce přehled o lodích, které jsou na vodě

## Registrace lodí

* všechny lodě (plavidla) na akci, která se budou hlídat se zaregistrují v PlachtISu
* registrace bude obsahovat
  * informace o lodi
    * třída (z předvybraných možností)
    * doplnění třídy (volné textové pole pro upřesnění)
    * plachetní číslo (pokud existuje)
    * jméno lodi
    * popis (barvy, významné prvky, apod.)
    * plocha plachet
  * informace o majiteli
    * číslo přístavu (oddílu)
    * název přístavu (oddílu)
    * jméno kontaktní osoby
    * kontaktní telefon
* registrovat loď může kterýkoliv uživatel PlachtISu, jen on pak může její údaje upravovat či ji smazat

* zobrazit si registrované lodě včetně detailů může každý uživatel PlachtISu
* organizátoři v Infostánku budou moci editovat registrované lodě a případně přidávat nové i v průběhu akce

Volitelné / doplňkové funkcionality:
* systém může na základě vyplnění Plachetního čísla předvyplnit údaje o lodi z Plachetního registru
* systém může předvyplnit údaje o majiteli na základě údajů o Jednotce registrované daným uživatelem

## Registrace posádek

* slouží jako podklad pro řízení závodu
* posádka se registruje vždy do konkrétní kategorie
  * Q (žabičky a vlčata)
  * S (skautky a skauti)
  * R (rangers a roveři)
  * D (dospělí)
  * SN (skautští námořníci)
  * DN (dospělí námořníci)
  * OŽ (Open Žáci)
  * OD (Open Dospělí)
  * MS (Modrá stuha)
* posádka se registruje vždy s konkrétní zaregistrovanou lodí (přičemž jedna loď v jedné kategorii může být použita jen pro jednu posádku)
* posádka má členy (Kormidelník + až 4 Lodníci), kteří jsou v PlachtISu zaregistrování jako Účastníci akce
* pro registraci posádky musí mít daný uživatel PlachtISu oprávnění k dané Lodi (což mají všichni) a k daným Účastníkům (což má aktuálně pouze ten kdo je zaregistroval a jeho Editoři)
  * z důvodu možnosti "půjčování" členů posádek zavedeme do PlachtISu možnost "půjčit / zviditelnit" daného Účastníka jinému uživateli

Volitelné funkcionality:
* PlachtIS bude kontrolovat platnost registrace dané Posádky vůči pravidlům (plocha plachet, počet a věk účastníkům) a bude zvýrazňovat problémy; nesmí ale registraci Posádky odmítat


## Export dat pro závod

Po ukončení registrací do závodu musí PlachtIS umožnit administrátorům exportovat data o lodích a o přihlášených posádkách pro potřeby řízení závodu.

## Modul pro plavenky

PlachtIS bude zajišťovat dva druhy funkcionality -- podklady pro tisk fyzických plavenek a evidenci plavenek na místě.

Plavenky budou mít čtyři barevně odlišené kategorie:
* pramice P550
* plachetnice
* ostatní lodě
* _náhradní_ (vydají se při ztrátě originální plavenky)

Každá plavenka bude mít svůj unikátní kód, s různým prefixem pro různé barvy. U plachetnic bude kód ideálně vycházet z plachetního čísla. Kódy budou tvořit číselnou řadu.

Plavenky budou fyzicky realizovány jako RFID karty, jejichž UID budou načítat čtečky.

### Plavenky v PlachtISu

PlachtIS umožní administrátorům vytvářet, editovat a mazat plavenky, včetně funkce pro smazání všech.

Plavenka bude obsahovat pouze svůj kód (a volitelně UID své RFID karty); volitelně může být přiřazena k určité lodi. Jedna loď může mít i více plavenek (ztráta).

PlachtIS umožní jednoduše vytvořit plavenky pro celou akci, což bude zahrnovat:
* plavenky pro všechny registrované lodě (vytvoření plavenky a přiřazení); do kódu se použije plachetní číslo, existuje-li (musí být volné, jinak chyba!) 
* rezervní plavenky pro každou kategorii (počet se zadá při vytváření); do kódu se použije vyšší číslo
* náhradní plavenky (počet se zadá při vytváření)

Předpokládaným způsobem zadání plavenek do PlachtISu je tento způsob, detaily pak bude možné dělat jednotlivě.

### Export údajů k natištění

PlachtIS umožní export plavenek ve formátu, který poslouží jako podklad tiskárně pro potisk fyzických plavenek.

Dle aktuální domluvy by každá plavenka měla obsahovat:
* číslo/kód plavenky
* lodní třídu
* plachetní číslo
* jméno lodi
* vlastníka (přístav)

Náhradní plavenky a rezervní plavenky v každé kategorii budou obsahovat pouze číslo/kód plavenky.

Formát upřesní Erik, mělo by jít o CSV.

### Evidence plavenek na akci

PlachtIS bude ke každé plavence udržovat stavovou informaci, kde se nachází:
* NA BŘEHU (výchozí stav; plavenka je fyzicky na místě)
* NA VODĚ (plavenka byla fyzicky vydána; musí být přiřazena k určité lodi)
* ZTRACENA (posádka nahlásí, že plavenku ztratila; loď se v tu chvíli bere jako na břehu; obsluha přiřadí dané lodi Náhradní plavenku)

Tyto změny budou administrátoři moci zadávat do systému, přičemž pro vyhledání plavenky bude možné použít i údaje o lodi, ke které je přiřazena.

Ke každé lodi může být v danou chvíli přiřazena pouze jedna plavenka, která není ZTRACENA. Pokud se fyzicky plavenka opět najde, posádka vrátí Náhradní plavenku, jejíž přiřazení k dané lodi se zruší a stav původní plavenky se obnoví na NA BŘEHU.

PlachtIS umožní administrátorům kdykoliv zobrazit seznam všech lodí, jejichž plavenky jsou NA VODĚ, a to včetně:
* názvu lodi
* třídy lodi
* popisu
* kontaktu na majitele

PlachtIS bude zaznamenávat všechny změny stavů plavenek včetně času a umožní administrátorům náhled do těchto záznamů:
* do všech
* pro konkrétní loď

Z tohoto důvodu bude asi užitečné zaznamenávat změny stavů k dané lodi, s údajem která plavenka byla použita.

### Změny stavu přes čtečky karet

PlachtIS bude obsahovat API, které umožní použít čtečky RFID karet k automatizaci změn stavů plavenek.

Po přiložení karty ke čtečce odešle čtečka API požadavek na PlachtIS s UID plavenky a identifikací čtečky. PlachtIS bude interpretovat tyto načtení jako změny stavu dané plavenky na stav "NA VODĚ" a "NA BŘEHU" podle identifikace čtečky.
PlachtIS také na správně formovaný API požadavek odešle odpověď s informacemi o lodi navázané na plavenku a s aktuálním stavem plavenky.

#### Spárování plavenek

Při vytvoření plavenek v PlachtISu nebude známé jejich UID; při načtení plavenky čtečkou zase nelze zjistit jiné informace.
PlachtIS tedy umožní spárovat UID plavenek s jejich daty v PlachtISu, a to uživatelsky přívětivou formou (například kliknutí na tlačítko "Spárovat" u plavenky způsobí, že příští přiložení plavenky ke čtečce nezmění její stav, ale spáruje její UID s danou plavenkou).


