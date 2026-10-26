// expect: use-after-free
int main() {
    int mode = 0;
    own int* p = alloc(4);
    if (mode == 1) {
        free(p);
    }
    *p = 5;
    free(p);
    return 0;
}
