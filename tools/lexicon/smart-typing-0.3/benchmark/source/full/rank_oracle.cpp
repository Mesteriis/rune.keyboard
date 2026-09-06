#include <algorithm>
#include <codecvt>
#include <fstream>
#include <iostream>
#include <locale>
#include <sstream>
#include <string>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <vector>
using U=std::u32string;
std::wstring_convert<std::codecvt_utf8<char32_t>,char32_t> cv;
std::vector<std::string> split(const std::string&s){std::vector<std::string>p;std::stringstream in(s);std::string t;while(std::getline(in,t,'\t'))p.push_back(t);return p;}
int dl(const U&a,const U&b){int h[34][34];int n=a.size(),m=b.size(),inf=n+m;h[0][0]=inf;for(int i=0;i<=n;i++){h[i+1][0]=inf;h[i+1][1]=i;}for(int j=0;j<=m;j++){h[0][j+1]=inf;h[1][j+1]=j;}std::unordered_map<char32_t,int>last;for(int i=1;i<=n;i++){int db=0;for(int j=1;j<=m;j++){int i1=last[b[j-1]],j1=db,cost=1;if(a[i-1]==b[j-1]){cost=0;db=j;}h[i+1][j+1]=std::min({h[i][j]+cost,h[i+1][j]+1,h[i][j+1]+1,h[i1][j1]+i-i1+j-j1-1});}last[a[i-1]]=i;}return h[n+1][m+1];}
int adjacency(const U&q,const U&w,const std::string&lang){if(q.size()!=w.size())return 1;std::vector<int>diff;for(int i=0;i<(int)q.size();i++)if(q[i]!=w[i])diff.push_back(i);if(diff.size()==2){int i=diff[0],j=diff[1];if(j==i+1&&q[i]==w[j]&&q[j]==w[i])return 0;}if(diff.size()==1){auto rows=lang=="ru"?std::vector<U>{U"йцукенгшщзхъ",U"фывапролджэ",U"ячсмитьбю"}:std::vector<U>{U"qwertyuiop",U"asdfghjklñ",U"zxcvbnm"};int i=diff[0];for(auto&r:rows){auto a=r.find(q[i]),b=r.find(w[i]);if(a!=U::npos&&b!=U::npos&&std::abs((int)a-(int)b)==1)return 0;}}return 1;}
int main(int argc,char**argv){if(argc!=6)return 2;std::string lang=argv[1],line;std::unordered_map<std::string,int>freq,ids;std::unordered_set<std::string>wanted;
 std::ifstream oracle(argv[4]);while(std::getline(oracle,line)){auto p=split(line);for(size_t i=1;i<p.size();i++)wanted.insert(p[i]);}oracle.clear();oracle.seekg(0);
 std::ifstream frequencies(argv[3]);std::getline(frequencies,line);while(std::getline(frequencies,line)){auto p=split(line);freq[p[0]]=std::stoi(p[1]);}
 std::ifstream words(argv[2]);int id=0;while(std::getline(words,line)){id++;if(wanted.count(line))ids[line]=id;}if(ids.size()!=wanted.size())throw std::runtime_error("oracle candidate outside source");
 std::ofstream out(argv[5]);std::ofstream all(std::string(argv[5])+".all-ids.tsv");int queries=0;while(std::getline(oracle,line)){auto p=split(line);auto q=cv.from_bytes(p[0]);std::vector<std::tuple<int,int,int,int>>ranked;
 for(size_t i=1;i<p.size();i++){auto w=cv.from_bytes(p[i]);int d=dl(q,w);if(d<1||d>(q.size()<5?1:2))throw std::runtime_error("bad full oracle neighbor");auto it=freq.find(p[i]);ranked.emplace_back(d,adjacency(q,w,lang),it==freq.end()?2147483647:it->second,ids.at(p[i]));}
 std::sort(ranked.begin(),ranked.end());all<<p[0];for(const auto& candidate:ranked)all<<'\t'<<std::get<3>(candidate);all<<'\n';out<<p[0]<<'\t'<<ranked.size();for(size_t i=0;i<std::min(size_t(7),ranked.size());i++)out<<'\t'<<std::get<3>(ranked[i]);out<<'\n';queries++;}
 if(dl(U"CA",U"ABC")!=2||dl(U"😀a",U"a😀")!=1||dl(U"a😀b",U"ab😀")!=1)throw std::runtime_error("unrestricted Unicode sentinel failure");
 std::cout<<lang<<" ranked "<<queries<<" full-neighborhood references; exact independent unit DL + adjacency + rank + lexical-id\n";
}
