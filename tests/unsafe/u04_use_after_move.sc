// expect: use-after-move
int main() {
    own int* a = alloc(4);
    *a = 3;
    own int* b = a;
    print(*a);
    free(b);
    return 0;
}
