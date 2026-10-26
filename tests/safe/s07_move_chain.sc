// expect: safe
int main() {
    own int* a = alloc(4);
    *a = 1;
    own int* b = a;
    own int* c = b;
    print(*c);
    free(c);
    return 0;
}
