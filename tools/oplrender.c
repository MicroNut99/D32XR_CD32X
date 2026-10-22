/* oplrender.c - tools/make_sigil_cdda.sh: renders a MIDI through libADLMIDI (Nuked OPL3, DMX instruments, DMX volume model) to a 44.1 kHz WAV: one pass, then TAIL seconds of the loop fading out. Built against libADLMIDI (github.com/Wohlstand/libADLMIDI). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <adlmidi.h>
static void w32(FILE*f,unsigned v){fputc(v,f);fputc(v>>8,f);fputc(v>>16,f);fputc(v>>24,f);}
static void w16(FILE*f,unsigned v){fputc(v,f);fputc(v>>8,f);}
int main(int c,char**v){
  if(c<2){int n=adl_getBanksCount();const char*const*b=adl_getBankNames();for(int i=0;i<n;i++)printf("%d %s\n",i,b[i]);return 0;}
  /* render in.mid out.wav bank [tail_seconds] : one pass, then tail_seconds of the loop fading out */
  int bank=atoi(v[3]); double tail=c>4?atof(v[4]):3.0;
  struct ADL_MIDIPlayer*p=adl_init(44100);
  adl_switchEmulator(p,ADLMIDI_EMU_NUKED);
  adl_setNumChips(p,1);
  if(adl_setBank(p,bank)<0){fprintf(stderr,"%s\n",adl_errorInfo(p));return 1;}
  adl_setVolumeRangeModel(p,ADLMIDI_VolumeModel_DMX);
  adl_setLoopEnabled(p,1);
  if(adl_openFile(p,v[1])<0){fprintf(stderr,"%s\n",adl_errorInfo(p));return 1;}
  FILE*f=fopen(v[2],"wb"); fwrite("RIFF\0\0\0\0WAVEfmt ",1,16,f); w32(f,16);w16(f,1);w16(f,2);w32(f,44100);w32(f,44100*4);w16(f,4);w16(f,16);
  fwrite("data\0\0\0\0",1,8,f);
  short buf[4096]; long n=0; int got;
  double len=adl_totalTimeLength(p); long total=(long)((len+tail)*44100)*2, fade=(long)(tail*44100)*2;
  while(n<total){int k=total-n>4096?4096:(int)(total-n); got=adl_play(p,k,buf); if(got<=0)break;
    for(int i=0;i<got;i++){long pos=n+i; if(pos>total-fade){double g=(double)(total-pos)/fade; buf[i]=(short)(buf[i]*g*g);}}
    fwrite(buf,2,got,f);n+=got;}
  fseek(f,4,SEEK_SET);w32(f,36+n*2);fseek(f,40,SEEK_SET);w32(f,n*2);fclose(f);adl_close(p);
  fprintf(stderr,"%s: %.1f s\n",v[2],n/2/44100.0);return 0;}
