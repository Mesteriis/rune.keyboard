// Offline-only wrapper: uses the pinned Hunspell library, never linked into the APK.
#include "hunspell.hxx"
#include "hashmgr.hxx"
#include <iostream>
#include <memory>
#include <string>

int main(int argc, char** argv) {
  if (argc != 3 && !(argc == 4 && std::string(argv[3]) == "--flags")) {
    std::cerr << "usage: spell_oracle dictionary.aff dictionary.dic [--flags]\n";
    return 2;
  }
  Hunspell dictionary(argv[1], argv[2]);
  if (dictionary.get_dict_encoding() != "UTF-8") {
    std::cerr << "only UTF-8 dictionaries supported\n";
    return 2;
  }
  std::string word;
  std::unique_ptr<HashMgr> flags;
  if (argc == 4) flags = std::make_unique<HashMgr>(argv[2], argv[1]);
  while (std::getline(std::cin, word)) {
    if (flags) {
      std::vector<unsigned short> decoded;
      flags->decode_flags(decoded, word, nullptr);
      std::cout << flags->decode_flag(word) << '\t';
      for (std::size_t i = 0; i < decoded.size(); ++i) {
        if (i) std::cout << ',';
        std::cout << decoded[i];
      }
      std::cout << '\t' << word << '\n';
    } else {
      std::cout << (dictionary.spell(word) ? "1\t" : "0\t") << word << '\n';
    }
  }
  return std::cin.bad() || !std::cout ? 1 : 0;
}
