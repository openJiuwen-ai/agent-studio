# -*- coding: utf-8 -*-
"""用 Kerby 自身 API 构造带真实 principal 的 keytab(零格式猜测)。

运行: java -cp kerb-util.jar:kerb-core.jar:kerby-util.jar:kerby-asn1.jar:kerb-crypto.jar GenKeytab
"""
import subprocess
import sys
import os

JAVA_SRC = r'''
import org.apache.kerby.kerberos.kerb.keytab.Keytab;
import org.apache.kerby.kerberos.kerb.keytab.KeytabEntry;
import org.apache.kerby.kerberos.kerb.type.base.PrincipalName;
import org.apache.kerby.kerberos.kerb.type.base.EncryptionKey;
import org.apache.kerby.kerberos.kerb.type.base.EncryptionType;
import java.io.File;

public class GenKeytab {
    public static void main(String[] args) throws Exception {
        // Test 1: 单组件 user@REALM.COM
        Keytab kt1 = new Keytab();
        kt1.addEntry(createEntry("user@REALM.COM"));
        kt1.store(new File("test_single_component.kt"));
        System.out.println("test_single_component.kt: " + new File("test_single_component.kt").length() + " bytes");

        // Test 2: 多组件 lakesearch/host@REALM.COM
        Keytab kt2 = new Keytab();
        kt2.addEntry(createEntry("lakesearch/host@REALM.COM"));
        kt2.store(new File("test_multi_component.kt"));
        System.out.println("test_multi_component.kt: " + new File("test_multi_component.kt").length() + " bytes");

        // Test 3: 混合(多组件+不同realm+4组件)
        Keytab kt3 = new Keytab();
        kt3.addEntry(createEntry("lakesearch/host/primary@REALM.COM"));
        kt3.addEntry(createEntry("user2@TEST.REALM"));
        kt3.addEntry(createEntry("service/node/instance/domain@REALM.COM"));
        kt3.store(new File("test_mixed_principals.kt"));
        System.out.println("test_mixed_principals.kt: " + new File("test_mixed_principals.kt").length() + " bytes");

        // Test 4: 重复 entry(去重验证)
        Keytab kt4 = new Keytab();
        kt4.addEntry(createEntry("user@REALM.COM"));
        kt4.addEntry(createEntry("user@REALM.COM"));
        kt4.addEntry(createEntry("lakesearch/host@REALM.COM"));
        kt4.store(new File("test_dedup.kt"));
        System.out.println("test_dedup.kt: " + new File("test_dedup.kt").length() + " bytes");

        // 验证:读回并打印 principal(Kerby 输出的真实形态——归一化前)
        for (String f : new String[]{"test_single_component.kt", "test_multi_component.kt",
                                     "test_mixed_principals.kt", "test_dedup.kt"}) {
            Keytab read = Keytab.loadKeytab(new File(f));
            System.out.println(f + " principals:");
            read.getPrincipals().forEach(p ->
                System.out.println("  getName()=[" + p.getName() + "]"
                    + " realm=[" + p.getRealm() + "]"));
        }
    }

    private static KeytabEntry createEntry(String fullPrincipal) {
        PrincipalName pn = new PrincipalName(fullPrincipal);
        EncryptionKey key = new EncryptionKey(EncryptionType.AES128_CTS, new byte[16]);
        return new KeytabEntry(pn,
            new org.apache.kerby.kerberos.kerb.type.KerberosTime(),
            1, key);
    }
}
'''

def main():
    lib = r"D:\project\openjiuwen\agent-studio\backend\studio-manager\target\lib"
    cp = ";".join([
        os.path.join(lib, "kerb-util-2.0.3.jar"),
        os.path.join(lib, "kerb-core-2.0.3.jar"),
        os.path.join(lib, "kerby-util-2.0.3.jar"),
        os.path.join(lib, "kerby-asn1-2.0.3.jar"),
        os.path.join(lib, "kerb-crypto-2.0.3.jar"),
        os.path.join(lib, "kerby-config-2.0.3.jar"),
        os.path.join(lib, "kerby-pkix-2.0.3.jar"),
    ])
    outdir = r"D:\project\openjiuwen\agent-studio\backend\studio-manager-service\src\test\resources"
    java_file = os.path.join(outdir, "GenKeytab.java")
    with open(java_file, "w", encoding="utf-8") as f:
        f.write(JAVA_SRC)

    # Compile
    r = subprocess.run(["javac", "-cp", cp, "-d", outdir, java_file],
                      capture_output=True, text=True)
    if r.returncode != 0:
        print("COMPILE FAILED:", r.stderr)
        sys.exit(1)

    # Run
    r = subprocess.run(["java", "-cp", cp + ";" + outdir, "GenKeytab"],
                      capture_output=True, text=True, cwd=outdir)
    print(r.stdout)
    if r.returncode != 0:
        print("RUN FAILED:", r.stderr)
        sys.exit(1)

    # Cleanup
    for f in ["GenKeytab.java", "GenKeytab.class"]:
        p = os.path.join(outdir, f)
        if os.path.exists(p):
            os.remove(p)

if __name__ == "__main__":
    main()
