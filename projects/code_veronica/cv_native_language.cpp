#include "cv_native_language_overlay.h"
#include "cv_appearance_prepare.h"
#include "cv_translation_patch.h"
#include <algorithm>
#include <array>
#include <map>
#include <mutex>
#include "zlib.h"
#include <cstdio>
#include <stdexcept>
namespace cv_native_language {
namespace {
using Resource=cv_appearance::Resource;using Bytes=std::vector<uint8_t>;
std::string normalize(std::string value){
 for(const char* locale:{"eng","fra","ger","ita","spa"}){
  const std::string from=std::string("biocv_tmp\\")+locale+"\\";
  size_t at=0;while((at=value.find(from,at))!=std::string::npos){value.replace(at+10,3,"usa");at+=from.size();}
 }
 return value;
}
Bytes normalize_bytes(const Bytes& bytes){
 std::string s(reinterpret_cast<const char*>(bytes.data()),bytes.size());s=normalize(std::move(s));return Bytes(s.begin(),s.end());
}
bool localizable(uint32_t type){
 // Only message tables and texture pixels are locale content. Keep every
 // original US script, model, map layout and hashed resource reference.
 return type==0x46c78353||type==0x6a76e771||type==0x241f5deb;
}
std::vector<Resource> load(const std::filesystem::path& file){
 std::vector<Resource> result;std::string error;
 if(!cv_appearance::load_archive_resources(file,result,error))throw std::runtime_error(error);
 return result;
}
// fork: minimal archive rewrite. The game stores an entry raw when its stored
// size equals its decoded size, and inflates it otherwise. Re-encoding every
// entry (encode_archive_resources) compressed rm_0010's 48-byte door/start
// position table to exactly 48 bytes: the game then read zlib bytes as
// positions and the player came out of that door about 2 m off. Here every
// untouched entry keeps its original stored bytes and table words; only the
// translated ones are re-stored (compressed if that is smaller, raw if not).
uint32_t rd32(const Bytes& b,size_t a){if(a+4>b.size())throw std::runtime_error("Truncated ARC");return uint32_t(b[a])<<24|uint32_t(b[a+1])<<16|uint32_t(b[a+2])<<8|b[a+3];}
void wr32(Bytes& b,size_t a,uint32_t v){for(unsigned i=0;i<4;i++)b[a+i]=uint8_t(v>>(24-i*8));}
Bytes sfh_unwrap(const Bytes& b,bool& wrapped){
 wrapped=b.size()>=16&&rd32(b,0)==0x00534648;if(!wrapped)return b;
 if(rd32(b,4)!=0x00010001)throw std::runtime_error("Unsupported SFH version");
 const size_t expected=rd32(b,8);Bytes out;out.reserve(expected);
 for(size_t at=0;at+16<=b.size()&&out.size()<expected;at+=0x20000){
  const size_t n=std::min({size_t(0x1fff0),b.size()-at-16,expected-out.size()});out.insert(out.end(),b.begin()+at+16,b.begin()+at+16+n);
 }
 if(out.size()!=expected)throw std::runtime_error("Truncated SFH payload");return out;
}
std::array<uint8_t,16> sfh_sum(const Bytes& b,size_t start,size_t n){
 const unsigned rotations[]={7,2,5,4,6,3,1,4,2,6,7,3,5,7,1,5},seeds[]={135,85,7,181,75,4,165,174,199,103,190,203,1,80,88,68};
 std::array<uint8_t,16> out{};for(unsigned j=0;j<16;j++){unsigned v=seeds[j];for(size_t at=j;at<n;at+=16)v+=b[start+at];v&=255;out[j]=uint8_t((v<<rotations[j])|(v>>(8-rotations[j])));}return out;
}
Bytes sfh_wrap(const Bytes& logical){
 Bytes out(16,0);wr32(out,0,0x00534648);wr32(out,4,0x00010001);wr32(out,8,uint32_t(logical.size()));
 for(size_t p=0;p<logical.size();p+=0x1fff0){
  Bytes chunk(logical.begin()+p,logical.begin()+p+std::min(size_t(0x1fff0),logical.size()-p));chunk.resize((chunk.size()+15)&~size_t(15));
  const auto sum=sfh_sum(chunk,0,chunk.size());out.insert(out.end(),chunk.begin(),chunk.end());out.insert(out.end(),sum.begin(),sum.end());
 }
 return out;
}
// replacements[i] non-null: new decoded bytes for entry i. Same table order.
Bytes rewrite_archive(const Bytes& file,const std::vector<const Bytes*>& replacements){
 bool wrapped=false;const Bytes arc=sfh_unwrap(file,wrapped);
 if(rd32(arc,0)!=0x00435241)throw std::runtime_error("Unsupported ARC");
 const size_t count=size_t(arc[6])<<8|arc[7],table=8+count*80;
 if(replacements.size()!=count||table>arc.size())throw std::runtime_error("ARC table mismatch");
 Bytes logical(arc.begin(),arc.begin()+table);size_t end=table;
 for(size_t i=0;i<count;i++){
  const size_t a=8+i*80;const uint32_t stored=rd32(arc,a+68),cap=rd32(arc,a+72),off=rd32(arc,a+76);
  if(off<table||size_t(off)+stored>arc.size())throw std::runtime_error("ARC entry outside archive");
  end=std::max(end,size_t(off)+stored);
  Bytes data;uint32_t new_cap=cap;
  if(replacements[i]){
   const Bytes& raw=*replacements[i];uLongf size=compressBound(uLong(raw.size()));Bytes packed(size);
   if(compress2(packed.data(),&size,raw.data(),uLong(raw.size()),Z_BEST_COMPRESSION)!=Z_OK)throw std::runtime_error("Compression failed");
   packed.resize(size);
   data=packed.size()<raw.size()?std::move(packed):raw;   // equal sizes would read as raw
   new_cap=uint32_t(raw.size()<<3)|(cap&7u);
  } else data.assign(arc.begin()+off,arc.begin()+off+stored);
  wr32(logical,a+68,uint32_t(data.size()));wr32(logical,a+72,new_cap);wr32(logical,a+76,uint32_t(logical.size()));
  logical.insert(logical.end(),data.begin(),data.end());
 }
 // Whatever followed the last entry (padding) is kept as it was.
 if(end<arc.size())logical.insert(logical.end(),arc.begin()+end,arc.end());
 return wrapped?sfh_wrap(logical):logical;
}
}
bool prepare_archive(const std::filesystem::path& original,const std::filesystem::path& translated,std::filesystem::path& result,std::string& error){
 static std::mutex mutex;std::lock_guard<std::mutex> guard(mutex);
 try{
  auto parent=translated.parent_path();
  // Locate the locale directory under biocv_disc without depending on depth.
  auto locale=parent;while(locale.has_parent_path()&&locale.parent_path().filename()!="biocv_disc"){
   if(locale==locale.parent_path())throw std::runtime_error("Invalid locale root");locale=locale.parent_path();
  }
  if(locale.parent_path().filename()!="biocv_disc")throw std::runtime_error("Invalid locale root");
  const auto relative=translated.lexically_relative(locale);
  const auto english=locale.parent_path()/"eng"/relative;
  Bytes us,base,target;
  if(!cv_translation_patch::read(original,us)||!cv_translation_patch::read(english,base)||!cv_translation_patch::read(translated,target))throw std::runtime_error("Cannot read native locale source");
  const auto key=cv_translation_patch::hash(us)+cv_translation_patch::hash(base)+cv_translation_patch::hash(target);
  if(key.size()!=192)throw std::runtime_error("Cannot identify locale sources");
  const Bytes identity(key.begin(),key.end());
  result=std::filesystem::temp_directory_path()/"ps3recomp-mods/cv-us-language/v4"/cv_translation_patch::hash(identity)/"biocv_disc/usa"/relative;
  if(std::filesystem::is_regular_file(result)){error.clear();return true;}
  auto records=load(original),reference=load(english),localized=load(translated);
  using Key=std::pair<std::string,uint32_t>;
  std::map<Key,const Resource*> en,foreign;
  for(const auto& r:reference)if(!en.emplace(Key{normalize(r.name),r.type},&r).second)throw std::runtime_error("Ambiguous English locale resource");
  for(const auto& r:localized)if(!foreign.emplace(Key{normalize(r.name),r.type},&r).second)throw std::runtime_error("Ambiguous translated locale resource");
  unsigned changes=0;std::vector<const Bytes*> replacements(records.size(),nullptr);
  for(size_t i=0;i<records.size();i++){
   auto& r=records[i];
   if(!localizable(r.type))continue;
   const Key k{normalize(r.name),r.type};const auto a=en.find(k),b=foreign.find(k);
   if(a==en.end()||b==foreign.end())continue;
   auto replacement=normalize_bytes(b->second->bytes);
   if(replacement!=normalize_bytes(a->second->bytes)){r.bytes=std::move(replacement);replacements[i]=&r.bytes;++changes;}
  }
  if(!changes){result=original;error.clear();return true;}
  // Self-check: rewriting with no change must give the original file back,
  // byte for byte. Otherwise keep the US archive (English text in that file).
  if(rewrite_archive(us,std::vector<const Bytes*>(records.size(),nullptr))!=us){
   std::fprintf(stderr,"[LANGUAGE-US] %s: archive layout not reproducible; US file kept\n",relative.string().c_str());
   result=original;error.clear();return true;
  }
  auto generated=rewrite_archive(us,replacements);
  {std::vector<Resource> check;std::string why;auto probe=result;probe+=L".check";
   // the rewritten archive must decode to the intended resources
   std::filesystem::create_directories(result.parent_path());
   {std::ofstream s(probe,std::ios::binary|std::ios::trunc);s.write(reinterpret_cast<const char*>(generated.data()),generated.size());}
   const bool ok=cv_appearance::load_archive_resources(probe,check,why)&&check.size()==records.size()&&
       std::equal(check.begin(),check.end(),records.begin(),[](const Resource& x,const Resource& y){return x.name==y.name&&x.type==y.type&&x.bytes==y.bytes;});
   std::error_code ec;std::filesystem::remove(probe,ec);
   if(!ok){std::fprintf(stderr,"[LANGUAGE-US] %s: rewritten archive did not verify; US file kept\n",relative.string().c_str());result=original;error.clear();return true;}
  }
  std::filesystem::create_directories(result.parent_path());auto pending=result;pending+=L".tmp";
  {std::ofstream stream(pending,std::ios::binary|std::ios::trunc);stream.write(reinterpret_cast<const char*>(generated.data()),generated.size());stream.close();if(!stream)throw std::runtime_error("Cannot write native locale cache");}
  if(!MoveFileExW(pending.c_str(),result.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH))throw std::runtime_error("Cannot finalize native locale cache");
  std::fprintf(stderr,"[LANGUAGE-US] adapted %s: %u localized resources; US names/gameplay preserved\n",relative.string().c_str(),changes);
  error.clear();return true;
 }catch(const std::exception& e){result.clear();error=e.what();return false;}
}
}
