// expect: leak
int main() {
    own int* p = alloc(4);
    *p = 1;
    p = alloc(4);
    *p = 2;
    free(p);
    return 0;
}
