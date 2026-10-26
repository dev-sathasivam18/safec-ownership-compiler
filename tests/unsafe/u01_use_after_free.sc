// expect: use-after-free
int main() {
    own int* p = alloc(4);
    free(p);
    *p = 10;
    return 0;
}
