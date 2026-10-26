// expect: safe
int main() {
    int flag = 1;
    own int* p = alloc(4);
    *p = 0;
    if (flag == 1) {
        *p = 99;
    }
    print(*p);
    free(p);
    return 0;
}
