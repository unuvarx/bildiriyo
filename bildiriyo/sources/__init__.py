from . import ilangov, iskur, kariyerkapisi, resmigazete

# Sıra önemli: metni okunabilen kaynaklar önce işlenir; Kariyer Kapısı ilanları
# (metni yurt dışından okunamıyor) bu kaynaklardaki aynı ilanın kararını kullanır.
SOURCES = {
    "ilangov": ilangov,
    "resmigazete": resmigazete,
    "iskur": iskur,
    "kariyerkapisi": kariyerkapisi,
}
