#include "bm_oopsla.h"

int main(int argc, char * argv[]) {
  RECORD(4, x, n1, sn, loop1);

  x = 0;
  sn = 0;

  INIT_n1(unknown);
  INIT_loop1(unknown);

  while(1){
    PRINT_VARS();
    sn = sn + 1;
    x++;

    assert(sn == x*1 || sn == 0);
  }
  PRINT_VARS();

  assert(false);
}
