// expect: safe
int main() {
    int x = 1;
    {
        own int* inner = alloc(4);
        *inner = x + 1;
        print(*inner);
        free(inner);
    }
    return 0;
}
