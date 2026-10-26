// expect: double-free
int main() {
    int mode = 0;
    own int* p = alloc(4);
    *p = 1;
    if (mode == 1) {
        free(p);
    }
    free(p);
    return 0;
}
