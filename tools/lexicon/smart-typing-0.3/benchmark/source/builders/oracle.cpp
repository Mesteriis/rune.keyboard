#include <algorithm>
#include <array>
#include <codecvt>
#include <fstream>
#include <iostream>
#include <locale>
#include <string>
#include <unordered_map>
#include <vector>
// Full unrestricted Damerau-Levenshtein, independent of Kotlin traversal.
int dl(const std::u32string&a,const std::u32string&b){
 int h[34][34];int n=a.size(),m=b.size(),inf=n+m;h[0][0]=inf;
 for(int i=0;i<=n;i++){h[i+1][0]=inf;h[i+1][1]=i;}
 for(int j=0;j<=m;j++){h[0][j+1]=inf;h[1][j+1]=j;}
 std::unordered_map<char32_t,int> last;
 for(int i=1;i<=n;i++){int db=0;for(int j=1;j<=m;j++){
  int i1=last[b[j-1]],j1=db,cost=1;if(a[i-1]==b[j-1]){cost=0;db=j;}
  h[i+1][j+1]=std::min({h[i][j]+cost,h[i+1][j]+1,h[i][j+1]+1,h[i1][j1]+i-i1-1+1+j-j1-1});
 }last[a[i-1]]=i;}return h[n+1][m+1];
}
int main(int argc,char**argv){if(argc!=4)return 2;std::wstring_convert<std::codecvt_utf8<char32_t>,char32_t>cv;std::vector<std::pair<std::string,std::u32string>> words;std::ifstream f(argv[1]);std::string s;while(std::getline(f,s))words.push_back({s,cv.from_bytes(s)});std::ifstream qf(argv[2]);std::ofstream out(argv[3]);while(std::getline(qf,s)){auto q=cv.from_bytes(s);int d=q.size()<5?1:2;out<<s;size_t count=0;for(auto&[str,w]:words)if(w!=q&&std::abs((int)w.size()-(int)q.size())<=d&&dl(w,q)<=d){out<<'\t'<<str;count++;}out<<'\n';std::cout<<s<<": "<<count<<" candidates\n";}}
