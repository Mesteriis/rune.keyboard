#include <algorithm>
#include <array>
#include <codecvt>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <locale>
#include <queue>
#include <set>
#include <string>
#include <vector>
using Rec=std::array<uint32_t,6>; // four-codepoint delete key, word length, ordinal
static_assert(sizeof(Rec)==24);
int main(int argc,char**argv){
 if(argc!=4)return 2;std::ifstream src(argv[1]);std::string out=argv[2],tmp=argv[3];std::filesystem::create_directories(tmp);
 std::wstring_convert<std::codecvt_utf8<char32_t>,char32_t> cv;std::vector<Rec> buf;buf.reserve(500000);std::vector<std::string> chunks;
 auto flush=[&](){if(buf.empty())return;std::sort(buf.begin(),buf.end());buf.erase(std::unique(buf.begin(),buf.end()),buf.end());auto p=tmp+"/chunk-"+std::to_string(chunks.size());std::ofstream f(p,std::ios::binary);f.write((char*)buf.data(),buf.size()*sizeof(Rec));chunks.push_back(p);buf.clear();};
 std::string s;uint32_t id=0;while(std::getline(src,s)){
  auto w=cv.from_bytes(s);auto p=w.substr(0,4);std::set<std::u32string> keys{p},level{p};
  for(int d=0;d<2;d++){std::set<std::u32string> next;for(auto&k:level)for(size_t j=0;j<k.size();j++){auto q=k;q.erase(j,1);next.insert(q);keys.insert(q);}level=std::move(next);}
  for(auto&k:keys){Rec r{};for(size_t j=0;j<k.size();j++)r[j]=k[j];r[4]=w.size();r[5]=id;buf.push_back(r);if(buf.size()>=500000)flush();}id++;
 }flush();
 struct Head{Rec r;size_t file;bool operator>(const Head&o)const{return r>o.r;}};
 std::vector<std::ifstream> fs;std::priority_queue<Head,std::vector<Head>,std::greater<Head>> heap;
 for(size_t i=0;i<chunks.size();i++){fs.emplace_back(chunks[i],std::ios::binary);Rec r;if(fs.back().read((char*)&r,sizeof r))heap.push({r,i});}
 std::ofstream f(out,std::ios::binary);uint32_t header[4]={0x314c4452,id,4,24};f.write((char*)header,16);uint64_t n=0;
 while(!heap.empty()){auto h=heap.top();heap.pop();f.write((char*)&h.r,sizeof h.r);n++;Rec r;if(fs[h.file].read((char*)&r,sizeof r))heap.push({r,h.file});}
 for(auto&p:chunks)std::filesystem::remove(p);std::filesystem::remove(tmp);std::cout<<id<<" words, "<<n<<" postings\n";
}
