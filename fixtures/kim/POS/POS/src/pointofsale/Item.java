/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package pointofsale;

/**
 *
 * @author kim2
 */
public class Item {
    private int ID;
    private String name;
    private double price;


    public Item(int ID, String name, double price) {
        this.ID = ID;
        this.name = name;
        this.price = price;
    }

    public String getName() {
        return name;
    }
    
    
    public double getPrice() {
        return price;
    }

    public int getID() {
        return ID;
    }
    
}
