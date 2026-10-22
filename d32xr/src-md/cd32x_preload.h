/* CD32X: the WADs kept in the 16 MB RAM cart. The build (tools/make_preload.py) writes this
   table for its disc into build/d32xr/src-md; this default is empty (no preload: every file
   is read from the CD). */
#define CD32X_PRELOAD_COUNT 0
static const cd32x_preload_t cd32x_preload[CD32X_PRELOAD_COUNT + 1] = {
    { "", 0, 0 }
};
