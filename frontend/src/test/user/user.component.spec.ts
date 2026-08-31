// xdescribe：pre-existing 空用例样板（describe 内只有类定义、零个 it()，Jasmine 报 afterAll "No specs found"），
// 与本功能（DSL 版本对比阶段一）无关，测试入口恢复前从未跑过。待单独补 it() 或删除，先明确跳过。
xdescribe('user test (pre-existing 空用例样板，待单独处理)', () => {
  // ==================== 基础类型和接口定义 ====================
  interface User {
    id: number;
    name: string;
    email: string;
    templateNum: number;
    isActive: boolean;
    roles: string[];
    createdAt: Date;
    profile?: UserProfile;
  }

  interface UserProfile {
    avatar: string;
    bio: string;
    location: string;
  }

  interface Product {
    id: string;
    name: string;
    price: number;
    category: string;
    stock: number;
    tags: string[];
    metadata: Record<string, any>;
  }

  interface Order {
    id: string;
    userId: number;
    products: OrderItem[];
    total: number;
    status: OrderStatus;
    createdAt: Date;
    updatedAt: Date;
  }

  interface OrderItem {
    productId: string;
    quantity: number;
    price: number;
  }

  enum OrderStatus {
    PENDING = 'pending',
    PROCESSING = 'processing',
    SHIPPED = 'shipped',
    DELIVERED = 'delivered',
    CANCELLED = 'cancelled'
  }

// ==================== 工具函数 ====================
  function generateRandomString(length: number): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < length; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
  }

  function generateRandomNumber(min: number, max: number): number {
    return Math.floor(Math.random() * (max - min + 1)) + min;
  }

  function generateRandomEmail(): string {
    const domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'example.com'];
    const username = generateRandomString(8).toLowerCase();
    const domain = domains[Math.floor(Math.random() * domains.length)];
    return `${username}@${domain}`;
  }

// ==================== 测试数据工厂 ====================
  class TestDataFactory {
    static createUser(overrides?: Partial<User>): User {
      const id = generateRandomNumber(1, 10000);
      return {
        id,
        name: `User_${id}`,
        email: generateRandomEmail(),
        templateNum: generateRandomNumber(18, 65),
        isActive: Math.random() > 0.5,
        roles: ['user'],
        createdAt: new Date(),
        ...overrides
      };
    }

    static createProduct(overrides?: Partial<Product>): Product {
      return {
        id: `prod_${generateRandomString(8)}`,
        name: `Product ${generateRandomString(5)}`,
        price: parseFloat((Math.random() * 1000).toFixed(2)),
        category: ['Electronics', 'Clothing', 'Books', 'Food'][Math.floor(Math.random() * 4)],
        stock: generateRandomNumber(0, 100),
        tags: ['featured', 'new', 'sale'].slice(0, generateRandomNumber(0, 3)),
        metadata: {},
        ...overrides
      };
    }

    static createOrder(overrides?: Partial<Order>): Order {
      const now = new Date();
      return {
        id: `order_${generateRandomString(10)}`,
        userId: generateRandomNumber(1, 1000),
        products: [],
        total: 0,
        status: OrderStatus.PENDING,
        createdAt: now,
        updatedAt: now,
        ...overrides
      };
    }
  }

// ==================== 业务逻辑类（待测试） ====================
  class UserService {
    private users: Map<number, User> = new Map();
    private nextId: number = 1;

    createUser(userData: Omit<User, 'id' | 'createdAt'>): User {
      if (!userData.name || userData.name.trim().length === 0) {
        throw new Error('Name is required');
      }

      if (!userData.email.includes('@')) {
        throw new Error('Invalid email format');
      }

      const user: User = {
        ...userData,
        id: this.nextId++,
        createdAt: new Date()
      };

      this.users.set(user.id, user);
      return user;
    }

    getUserById(id: number): User | undefined {
      return this.users.get(id);
    }

    updateUser(id: number, updates: Partial<Omit<User, 'id' | 'createdAt'>>): User | undefined {
      const user = this.users.get(id);
      if (!user) return undefined;

      const updatedUser = { ...user, ...updates };
      this.users.set(id, updatedUser);
      return updatedUser;
    }

    deleteUser(id: number): boolean {
      return this.users.delete(id);
    }

    getAllUsers(): User[] {
      return Array.from(this.users.values());
    }

    getActiveUsers(): User[] {
      return this.getAllUsers().filter(user => user.isActive);
    }

    getUsersByAgeRange(min: number, max: number): User[] {
      return this.getAllUsers().filter(user => user.templateNum >= min && user.templateNum <= max);
    }
  }

  class ProductService {
    private products: Map<string, Product> = new Map();

    addProduct(product: Product): Product {
      if (this.products.has(product.id)) {
        throw new Error(`Product with ID ${product.id} already exists`);
      }

      if (product.price <= 0) {
        throw new Error('Price must be greater than 0');
      }

      if (product.stock < 0) {
        throw new Error('Stock cannot be negative');
      }

      this.products.set(product.id, product);
      return product;
    }

    getProductById(id: string): Product | undefined {
      return this.products.get(id);
    }

    updateStock(productId: string, quantity: number): boolean {
      const product = this.products.get(productId);
      if (!product) return false;

      const newStock = product.stock + quantity;
      if (newStock < 0) {
        throw new Error('Insufficient stock');
      }

      product.stock = newStock;
      return true;
    }

    getProductsByCategory(category: string): Product[] {
      return Array.from(this.products.values())
        .filter(product => product.category === category);
    }

    getProductsInStock(): Product[] {
      return Array.from(this.products.values())
        .filter(product => product.stock > 0);
    }

    searchProducts(keyword: string): Product[] {
      const lowerKeyword = keyword.toLowerCase();
      return Array.from(this.products.values())
        .filter(product =>
          product.name.toLowerCase().includes(lowerKeyword) ||
          product.tags.some(tag => tag.toLowerCase().includes(lowerKeyword))
        );
    }
  }

  class OrderService {
    private orders: Map<string, Order> = new Map();
    private productService: ProductService;

    constructor(productService: ProductService) {
      this.productService = productService;
    }

    createOrder(userId: number, items: Array<{productId: string, quantity: number}>): Order {
      if (items.length === 0) {
        throw new Error('Order must contain at least one item');
      }

      const orderItems: OrderItem[] = [];
      let total = 0;

      for (const item of items) {
        const product = this.productService.getProductById(item.productId);
        if (!product) {
          throw new Error(`Product ${item.productId} not found`);
        }

        if (product.stock < item.quantity) {
          throw new Error(`Insufficient stock for product ${product.name}`);
        }

        if (item.quantity <= 0) {
          throw new Error(`Invalid quantity for product ${product.name}`);
        }

        const itemTotal = product.price * item.quantity;
        orderItems.push({
          productId: item.productId,
          quantity: item.quantity,
          price: product.price
        });

        total += itemTotal;
      }

      for (const item of items) {
        this.productService.updateStock(item.productId, -item.quantity);
      }

      const order: Order = {
        id: `order_${Date.now()}_${generateRandomString(6)}`,
        userId,
        products: orderItems,
        total: parseFloat(total.toFixed(2)),
        status: OrderStatus.PENDING,
        createdAt: new Date(),
        updatedAt: new Date()
      };

      this.orders.set(order.id, order);
      return order;
    }

    updateOrderStatus(orderId: string, status: OrderStatus): boolean {
      const order = this.orders.get(orderId);
      if (!order) return false;

      const validTransitions: Record<OrderStatus, OrderStatus[]> = {
        [OrderStatus.PENDING]: [OrderStatus.PROCESSING, OrderStatus.CANCELLED],
        [OrderStatus.PROCESSING]: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
        [OrderStatus.SHIPPED]: [OrderStatus.DELIVERED],
        [OrderStatus.DELIVERED]: [],
        [OrderStatus.CANCELLED]: []
      };

      if (!validTransitions[order.status].includes(status)) {
        throw new Error(`Invalid status transition from ${order.status} to ${status}`);
      }

      order.status = status;
      order.updatedAt = new Date();
      return true;
    }

    getOrderById(orderId: string): Order | undefined {
      return this.orders.get(orderId);
    }

    getUserOrders(userId: number): Order[] {
      return Array.from(this.orders.values())
        .filter(order => order.userId === userId);
    }

    getOrdersByStatus(status: OrderStatus): Order[] {
      return Array.from(this.orders.values())
        .filter(order => order.status === status);
    }
  }

// ==================== 测试用例类 ====================
  class UserServiceTests {
    private userService: UserService;

    constructor() {
      this.userService = new UserService();
    }

    runAllTests(): void {
      console.log('Running UserService tests...');

      try {
        this.testCreateUser();
        this.testCreateUserValidation();
        this.testGetUserById();
        this.testUpdateUser();
        this.testDeleteUser();
        this.testGetAllUsers();
        this.testGetActiveUsers();
        this.testGetUsersByAgeRange();
        console.log('✅ All UserService tests passed!');
      } catch (error) {
        console.error('❌ UserService test failed:', error);
      }
    }

    private testCreateUser(): void {
      console.log('  Testing createUser...');

      const userData = {
        name: 'John Doe',
        email: '',
        templateNum: 30,
        isActive: true,
        roles: ['user', 'admin']
      };

      const user = this.userService.createUser(userData);

      if (!user.id) throw new Error('User should have an ID');
      if (user.name !== userData.name) throw new Error('Name mismatch');
      if (user.email !== userData.email) throw new Error('Email mismatch');
      if (user.templateNum !== userData.templateNum) throw new Error('templateNum mismatch');
      if (!user.createdAt) throw new Error('Missing createdAt');

      console.log('✅ createUser test passed');
    }

    private testCreateUserValidation(): void {
      console.log('  Testing createUser validation...');

      try {
        this.userService.createUser({
          name: '',
          email: '',
          templateNum: 25,
          isActive: true,
          roles: ['user']
        });
        throw new Error('Should have thrown error for empty name');
      } catch (error: any) {
        if (!error.message.includes('Name is required')) {
          throw new Error('Wrong error message for empty name');
        }
      }

      try {
        this.userService.createUser({
          name: 'Test User',
          email: 'invalid-email',
          templateNum: 25,
          isActive: true,
          roles: ['user']
        });
        throw new Error('Should have thrown error for invalid email');
      } catch (error: any) {
        if (!error.message.includes('Invalid email format')) {
          throw new Error('Wrong error message for invalid email');
        }
      }

      console.log('✅ createUser validation test passed');
    }

    private testGetUserById(): void {
      console.log('Testing getUserById...');

      const user = this.userService.createUser({
        name: 'Alice',
        email: '',
        templateNum: 28,
        isActive: true,
        roles: ['user']
      });

      const retrievedUser = this.userService.getUserById(user.id);

      if (!retrievedUser) throw new Error('User should be retrievable by ID');
      if (retrievedUser.id !== user.id) throw new Error('Retrieved user ID mismatch');

      const nonExistentUser = this.userService.getUserById(99999);
      if (nonExistentUser !== undefined) {
        throw new Error('Non-existent user should return undefined');
      }

      console.log('✅ getUserById test passed');
    }

    private testUpdateUser(): void {
      console.log('Testing updateUser...');

      const user = this.userService.createUser({
        name: 'Bob',
        email: '',
        templateNum: 35,
        isActive: false,
        roles: ['user']
      });

      const updatedUser = this.userService.updateUser(user.id, {
        name: 'Robert',
        templateNum: 36,
        isActive: true
      });

      if (!updatedUser) throw new Error('User should be updated');
      if (updatedUser.name !== 'Robert') throw new Error('Name not updated');
      if (updatedUser.templateNum !== 36) throw new Error('templateNum not updated');
      if (!updatedUser.isActive) throw new Error('isActive not updated');
      if (updatedUser.email !== user.email) throw new Error('Email should not change');

      const result = this.userService.updateUser(99999, { name: 'Test' });
      if (result !== undefined) {
        throw new Error('Updating non-existent user should return undefined');
      }

      console.log('✅ updateUser test passed');
    }

    private testDeleteUser(): void {
      console.log('Testing deleteUser...');

      const user = this.userService.createUser({
        name: 'Charlie',
        email: '',
        templateNum: 40,
        isActive: true,
        roles: ['user']
      });

      const deleteResult = this.userService.deleteUser(user.id);
      if (!deleteResult) throw new Error('Delete should return true for existing user');

      const retrievedUser = this.userService.getUserById(user.id);
      if (retrievedUser) throw new Error('User should be deleted');

      const deleteNonExistent = this.userService.deleteUser(99999);
      if (deleteNonExistent) throw new Error('Delete should return false for non-existent user');

      console.log('✅ deleteUser test passed');
    }

    private testGetAllUsers(): void {
      console.log('Testing getAllUsers...');

      this.userService.getAllUsers().forEach(user => {
        this.userService.deleteUser(user.id);
      });

      const users = [
        this.userService.createUser({
          name: 'User1',
          email: 'user1@example.com',
          templateNum: 20,
          isActive: true,
          roles: ['user']
        }),
        this.userService.createUser({
          name: 'User2',
          email: 'user2@example.com',
          templateNum: 30,
          isActive: false,
          roles: ['user']
        }),
        this.userService.createUser({
          name: 'User3',
          email: 'user3@example.com',
          templateNum: 40,
          isActive: true,
          roles: ['user']
        })
      ];

      const allUsers = this.userService.getAllUsers();

      if (allUsers.length !== 3) throw new Error(`Expected 3 users, got ${allUsers.length}`);

      users.forEach(expectedUser => {
        const found = allUsers.some(user => user.id === expectedUser.id);
        if (!found) throw new Error(`User ${expectedUser.id} not found in getAllUsers`);
      });

      console.log('✅ getAllUsers test passed');
    }

    private testGetActiveUsers(): void {
      console.log('Testing getActiveUsers...');

      this.userService.getAllUsers().forEach(user => {
        this.userService.deleteUser(user.id);
      });

      this.userService.createUser({
        name: 'Active1',
        email: 'active1@example.com',
        templateNum: 25,
        isActive: true,
        roles: ['user']
      });

      this.userService.createUser({
        name: 'Active2',
        email: 'active2@example.com',
        templateNum: 35,
        isActive: true,
        roles: ['user']
      });

      this.userService.createUser({
        name: 'Inactive',
        email: 'inactive@example.com',
        templateNum: 45,
        isActive: false,
        roles: ['user']
      });

      const activeUsers = this.userService.getActiveUsers();

      if (activeUsers.length !== 2) {
        throw new Error(`Expected 2 active users, got ${activeUsers.length}`);
      }

      activeUsers.forEach(user => {
        if (!user.isActive) throw new Error('All users in getActiveUsers should be active');
      });

      console.log('✅ getActiveUsers test passed');
    }

    private testGetUsersByAgeRange(): void {
      console.log('Testing getUsersByAgeRange...');

      this.userService.getAllUsers().forEach(user => {
        this.userService.deleteUser(user.id);
      });

      const users = [
        { name: 'Young', templateNum: 18 },
        { name: 'Middle1', templateNum: 25 },
        { name: 'Middle2', templateNum: 35 },
        { name: 'Senior', templateNum: 65 }
      ];

      users.forEach(userData => {
        this.userService.createUser({
          name: userData.name,
          email: `${userData.name.toLowerCase()}@example.com`,
          templateNum: userData.templateNum,
          isActive: true,
          roles: ['user']
        });
      });

      const ageRangeUsers = this.userService.getUsersByAgeRange(20, 40);

      if (ageRangeUsers.length !== 2) {
        throw new Error(`Expected 2 users in templateNum range 20-40, got ${ageRangeUsers.length}`);
      }

      ageRangeUsers.forEach(user => {
        if (user.templateNum < 20 || user.templateNum > 40) {
          throw new Error(`User templateNum ${user.templateNum} outside range 20-40`);
        }
      });

      console.log('✅ getUsersByAgeRange test passed');
    }
  }

  class ProductServiceTests {
    private productService: ProductService;

    constructor() {
      this.productService = new ProductService();
    }

    runAllTests(): void {
      console.log('\nRunning ProductService tests...');

      try {
        this.testAddProduct();
        this.testAddProductValidation();
        this.testGetProductById();
        this.testUpdateStock();
        this.testGetProductsByCategory();
        this.testGetProductsInStock();
        this.testSearchProducts();
        console.log('✅ All ProductService tests passed!');
      } catch (error) {
        console.error('❌ ProductService test failed:', error);
      }
    }

    private testAddProduct(): void {
      console.log('  Testing addProduct...');

      const product: Product = {
        id: 'test_product_1',
        name: 'Test Product',
        price: 29.99,
        category: 'Electronics',
        stock: 10,
        tags: ['new', 'featured'],
        metadata: { weight: '0.5kg' }
      };

      const addedProduct = this.productService.addProduct(product);

      if (addedProduct.id !== product.id) throw new Error('Product ID mismatch');
      if (addedProduct.price !== product.price) throw new Error('Product price mismatch');

      console.log('✅ addProduct test passed');
    }

    private testAddProductValidation(): void {
      console.log('Testing addProduct validation...');

      const product1: Product = {
        id: 'duplicate_id',
        name: 'Product 1',
        price: 10,
        category: 'Test',
        stock: 5,
        tags: [],
        metadata: {}
      };

      this.productService.addProduct(product1);

      try {
        const product2: Product = {
          id: 'duplicate_id',
          name: 'Product 2',
          price: 20,
          category: 'Test',
          stock: 5,
          tags: [],
          metadata: {}
        };

        this.productService.addProduct(product2);
        throw new Error('Should have thrown error for duplicate ID');
      } catch (error: any) {
        if (!error.message.includes('already exists')) {
          throw new Error('Wrong error message for duplicate ID');
        }
      }

      try {
        const invalidProduct: Product = {
          id: 'invalid_price',
          name: 'Invalid Product',
          price: 0,
          category: 'Test',
          stock: 5,
          tags: [],
          metadata: {}
        };

        this.productService.addProduct(invalidProduct);
        throw new Error('Should have thrown error for price <= 0');
      } catch (error: any) {
        if (!error.message.includes('Price must be greater than 0')) {
          throw new Error('Wrong error message for invalid price');
        }
      }

      try {
        const invalidProduct: Product = {
          id: 'invalid_stock',
          name: 'Invalid Product',
          price: 10,
          category: 'Test',
          stock: -5,
          tags: [],
          metadata: {}
        };
        this.productService.addProduct(invalidProduct);
        throw new Error('Should have thrown error for negative stock');
      } catch (error: any) {
        if (!error.message.includes('Stock cannot be negative')) {
          throw new Error('Wrong error message for negative stock');
        }
      }
      console.log('✅ addProduct validation test passed');
    }

    private testGetProductById(): void {
      console.log('Testing getProductById...');

      const product: Product = {
        id: 'get_by_id_test',
        name: 'Get By ID Test',
        price: 15.99,
        category: 'Books',
        stock: 20,
        tags: ['bestseller'],
        metadata: {}
      };

      this.productService.addProduct(product);
      const retrievedProduct = this.productService.getProductById('get_by_id_test');

      if (!retrievedProduct) throw new Error('Product should be retrievable by ID');
      if (retrievedProduct.name !== product.name) throw new Error('Product name mismatch');

      const nonExistent = this.productService.getProductById('non_existent_id');
      if (nonExistent !== undefined) throw new Error('Non-existent product should return undefined');

      console.log('✅ getProductById test passed');
    }

    private testUpdateStock(): void {
      console.log('Testing updateStock...');

      const product: Product = {
        id: 'stock_test',
        name: 'Stock Test Product',
        price: 25.00,
        category: 'Clothing',
        stock: 50,
        tags: [],
        metadata: {}
      };

      this.productService.addProduct(product);

      const result1 = this.productService.updateStock('stock_test', 20);
      if (!result1) throw new Error('Should successfully update stock');

      const productAfterAdd = this.productService.getProductById('stock_test');
      if (!productAfterAdd || productAfterAdd.stock !== 70) {
        throw new Error('Stock not increased correctly');
      }

      const result2 = this.productService.updateStock('stock_test', -30);
      if (!result2) throw new Error('Should successfully decrease stock');

      const productAfterSubtract = this.productService.getProductById('stock_test');
      if (!productAfterSubtract || productAfterSubtract.stock !== 40) {
        throw new Error('Stock not decreased correctly');
      }

      try {
        this.productService.updateStock('stock_test', -100);
        throw new Error('Should have thrown error for insufficient stock');
      } catch (error: any) {
        if (!error.message.includes('Insufficient stock')) {
          throw new Error('Wrong error message for insufficient stock');
        }
      }

      const resultNonExistent = this.productService.updateStock('non_existent', 10);
      if (resultNonExistent) throw new Error('Should return false for non-existent product');

      console.log('✅ updateStock test passed');
    }

    private testGetProductsByCategory(): void {
      console.log('Testing getProductsByCategory...');

      const testProducts = [
        { id: 'cat1_1', name: 'Electronics 1', category: 'Electronics', stock: 10 },
        { id: 'cat1_2', name: 'Electronics 2', category: 'Electronics', stock: 20 },
        { id: 'cat2_1', name: 'Books 1', category: 'Books', stock: 30 },
        { id: 'cat2_2', name: 'Books 2', category: 'Books', stock: 40 }
      ];

      testProducts.forEach(p => {
        this.productService.addProduct({
          id: p.id,
          name: p.name,
          price: 19.99,
          category: p.category,
          stock: p.stock,
          tags: [],
          metadata: {}
        });
      });

      const electronics = this.productService.getProductsByCategory('Electronics');
      if (electronics.length !== 2) {
        throw new Error(`Expected 2 electronics products, got ${electronics.length}`);
      }

      electronics.forEach(product => {
        if (product.category !== 'Electronics') {
          throw new Error(`Product ${product.name} has wrong category`);
        }
      });

      const books = this.productService.getProductsByCategory('Books');
      if (books.length !== 2) {
        throw new Error(`Expected 2 books, got ${books.length}`);
      }

      const nonExistent = this.productService.getProductsByCategory('NonExistent');
      if (nonExistent.length !== 0) {
        throw new Error('Non-existent category should return empty array');
      }

      console.log('✅ getProductsByCategory test passed');
    }

    private testGetProductsInStock(): void {
      console.log('Testing getProductsInStock...');

      const testProducts = [
        { id: 'instock_1', name: 'In Stock 1', stock: 10 },
        { id: 'instock_2', name: 'In Stock 2', stock: 5 },
        { id: 'outofstock', name: 'Out of Stock', stock: 0 },
        { id: 'negative', name: 'Negative Stock', stock: -5 }
      ];

      testProducts.forEach(p => {
        this.productService.addProduct({
          id: p.id,
          name: p.name,
          price: 9.99,
          category: 'Test',
          stock: p.stock,
          tags: [],
          metadata: {}
        });
      });

      const inStockProducts = this.productService.getProductsInStock();

      if (inStockProducts.length !== 2) {
        throw new Error(`Expected 2 products in stock, got ${inStockProducts.length}`);
      }

      inStockProducts.forEach(product => {
        if (product.stock <= 0) {
          throw new Error(`Product ${product.name} should have stock > 0`);
        }
      });

      console.log('✅ getProductsInStock test passed');
    }

    private testSearchProducts(): void {
      console.log('  Testing searchProducts...');

      const testProducts = [
        { id: 'search_1', name: 'Apple iPhone', tags: ['phone', 'apple'] },
        { id: 'search_2', name: 'Samsung Galaxy', tags: ['phone', 'android'] },
        { id: 'search_3', name: 'Apple MacBook', tags: ['laptop', 'apple'] },
        { id: 'search_4', name: 'Dell Laptop', tags: ['laptop', 'windows'] }
      ];

      testProducts.forEach(p => {
        this.productService.addProduct({
          id: p.id,
          name: p.name,
          price: 999.99,
          category: 'Electronics',
          stock: 10,
          tags: p.tags,
          metadata: {}
        });
      });

      const appleResults = this.productService.searchProducts('apple');
      if (appleResults.length !== 2) {
        throw new Error(`Expected 2 products with 'apple', got ${appleResults.length}`);
      }

      const phoneResults = this.productService.searchProducts('phone');
      if (phoneResults.length !== 2) {
        throw new Error(`Expected 2 products with 'phone', got ${phoneResults.length}`);
      }

      const noResults = this.productService.searchProducts('nonexistent');
      if (noResults.length !== 0) {
        throw new Error('Non-existent keyword should return empty array');
      }

      const caseResults = this.productService.searchProducts('APPLE');
      if (caseResults.length !== 2) {
        throw new Error('Search should be case-insensitive');
      }
      console.log('✅ searchProducts test passed');
    }
  }

  class OrderServiceTests {
    private orderService: OrderService;
    private readonly productService: ProductService;

    constructor() {
      this.productService = new ProductService();
      this.orderService = new OrderService(this.productService);
      this.setupTestProducts();
    }

    private setupTestProducts(): void {
      const testProducts = [
        { id: 'product_a', name: 'Product A', price: 10.00, stock: 100 },
        { id: 'product_b', name: 'Product B', price: 20.00, stock: 50 },
        { id: 'product_c', name: 'Product C', price: 30.00, stock: 25 },
        { id: 'product_d', name: 'Product D', price: 40.00, stock: 10 }
      ];

      testProducts.forEach(p => {
        this.productService.addProduct({
          id: p.id,
          name: p.name,
          price: p.price,
          category: 'Test',
          stock: p.stock,
          tags: [],
          metadata: {}
        });
      });
    }

    runAllTests(): void {
      console.log('\nRunning OrderService tests...');

      try {
        this.testCreateOrder();
        this.testCreateOrderValidation();
        this.testUpdateOrderStatus();
        console.log('✅ All OrderService tests passed!');
      } catch (error) {
        console.error('❌ OrderService test failed:', error);
      }
    }

    private testCreateOrder(): void {
      console.log('Testing createOrder...');

      const userId = 123;
      const items = [
        { productId: 'product_a', quantity: 2 },
        { productId: 'product_b', quantity: 1 }
      ];

      const order = this.orderService.createOrder(userId, items);

      if (!order.id) throw new Error('Order should have an ID');
      if (order.userId !== userId) throw new Error('User ID mismatch');
      if (order.products.length !== 2) throw new Error('Order should have 2 items');
      if (order.total !== 40.00) throw new Error(`Total should be 40.00, got ${order.total}`);
      if (order.status !== OrderStatus.PENDING) throw new Error('Order should be pending');

      const productA = this.productService.getProductById('product_a');
      if (!productA || productA.stock !== 98) {
        throw new Error('Product A stock should be reduced to 98');
      }

      const productB = this.productService.getProductById('product_b');
      if (!productB || productB.stock !== 49) {
        throw new Error('Product B stock should be reduced to 49');
      }

      console.log('✅ createOrder test passed');
    }

    private testCreateOrderValidation(): void {
      console.log('Testing createOrder validation...');

      try {
        this.orderService.createOrder(123, []);
        throw new Error('Should have thrown error for empty order');
      } catch (error: any) {
        if (!error.message.includes('at least one item')) {
          throw new Error('Wrong error message for empty order');
        }
      }

      try {
        this.orderService.createOrder(123, [
          { productId: 'non_existent', quantity: 1 }
        ]);
        throw new Error('Should have thrown error for non-existent product');
      } catch (error: any) {
        if (!error.message.includes('not found')) {
          throw new Error('Wrong error message for non-existent product');
        }
      }

      try {
        this.orderService.createOrder(123, [
          { productId: 'product_d', quantity: 100 }
        ]);
        throw new Error('Should have thrown error for insufficient stock');
      } catch (error: any) {
        if (!error.message.includes('Insufficient stock')) {
          throw new Error('Wrong error message for insufficient stock');
        }
      }

      try {
        this.orderService.createOrder(123, [
          { productId: 'product_a', quantity: 0 }
        ]);
        throw new Error('Should have thrown error for invalid quantity');
      } catch (error: any) {
        if (!error.message.includes('Invalid quantity')) {
          throw new Error('Wrong error message for invalid quantity');
        }
      }

      console.log('✅ createOrder validation test passed');
    }

    private testUpdateOrderStatus(): void {
      console.log('Testing updateStatus...');

      const order = this.orderService.createOrder(456, [
        { productId: 'product_c', quantity: 1 }
      ]);

      const result1 = this.orderService.updateOrderStatus(order.id, OrderStatus.PROCESSING);
      if (!result1) throw new Error('Should successfully update status to PROCESSING');

      const order1 = this.orderService.getOrderById(order.id);
      if (!order1 || order1.status !== OrderStatus.PROCESSING) {
        throw new Error('Order status should be PROCESSING');
      }

      try {
        this.orderService.updateOrderStatus(order.id, OrderStatus.DELIVERED);
        throw new Error('Should have thrown error for invalid status transition');
      } catch (error: any) {
        if (!error.message.includes('Invalid status transition')) {
          throw new Error('Wrong error message for invalid status transition');
        }
      }

      const result2 = this.orderService.updateOrderStatus(order.id, OrderStatus.SHIPPED);
      if (!result2) throw new Error('Should successfully update status to SHIPPED');

      const order2 = this.orderService.getOrderById(order.id);
      if (!order2 || order2.status !== OrderStatus.SHIPPED) {
        throw new Error('Order status should be SHIPPED');
      }

      const resultNonExistent = this.orderService.updateOrderStatus('non_existent', OrderStatus.PROCESSING);
      if (resultNonExistent) throw new Error('Should return false for non-existent order');

      console.log('✅ updateOrderStatus test passed');
    }
  }
});
